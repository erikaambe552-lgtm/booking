import os
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role
from accounts.permissions import IsServiceProvider, IsSystemAdmin, role_of
from destinations.models import BeachVenue, Category, Destination, MountainGuide

from . import realtime, services
from .models import BeachReservation, BookingStatus, GuideReservation, GuideSchedule, VenueSlot
from .serializers import (BeachBookingRequest, BeachReservationSerializer, GuideBookingRequest,
                          GuideReservationSerializer, GuideScheduleSerializer, StatusChangeRequest,
                          VenueSlotSerializer)

BEACH_QS = BeachReservation.objects.select_related("slot__venue__destination", "user").prefetch_related(
    "history__changed_by")
GUIDE_QS = GuideReservation.objects.select_related("schedule__guide__destination", "user").prefetch_related(
    "history__changed_by")


def _error(exc):
    return Response({"detail": str(exc), "code": exc.code}, status=exc.http_status)


def _combined(beach_qs, guide_qs):
    data = BeachReservationSerializer(beach_qs, many=True).data + GuideReservationSerializer(guide_qs, many=True).data
    return sorted(data, key=lambda r: r["created_at"], reverse=True)


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValidationError({"date": "Use YYYY-MM-DD."})


# --------------------------------------------------------------------------
# Availability checking (public)
# --------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([AllowAny])
def availability(request, slug):
    """GET /api/destinations/<slug>/availability/?date=YYYY-MM-DD (or ?days=30)
    BEACH    -> verified venues + their slots   (venue availability records)
    MOUNTAIN -> verified guides + their schedules (guide availability records)"""
    dest = get_object_or_404(Destination, slug=slug, is_published=True)
    now = timezone.now()
    if request.query_params.get("date"):
        d = _parse_date(request.query_params["date"])
        start = timezone.make_aware(datetime.combine(d, datetime.min.time()))
        end = start + timedelta(days=1)
    else:
        days = min(int(request.query_params.get("days", 60) or 60), 180)
        start, end = now, now + timedelta(days=days)
    start = max(start, now)

    payload = {"destination": dest.slug, "category": dest.category, "bookable": dest.is_bookable, "services": []}
    if not dest.is_bookable:
        return Response(payload)

    if dest.category == Category.BEACH:
        slots = VenueSlot.objects.filter(start_at__gte=start, start_at__lt=end).prefetch_related("reservations")
        venues = dest.venues.filter(is_active=True, is_verified=True).prefetch_related(Prefetch("slots", slots))
        for v in venues:
            payload["services"].append({
                "id": v.id, "name": v.name, "max_guests": v.max_guests,
                "slots": VenueSlotSerializer(v.slots.all(), many=True).data,
            })
    else:
        scheds = GuideSchedule.objects.filter(start_at__gte=start, start_at__lt=end).prefetch_related("reservations")
        guides = dest.guides.filter(is_active=True, is_verified=True).prefetch_related(Prefetch("schedules", scheds))
        for g in guides:
            payload["services"].append({
                "id": g.id, "name": g.display_name, "max_participants": g.max_participants,
                "slots": GuideScheduleSerializer(g.schedules.all(), many=True).data,
            })
    return Response(payload)


# --------------------------------------------------------------------------
# Creating reservations — two separate workflows
# --------------------------------------------------------------------------
class BeachBookingView(APIView):
    """POST /api/bookings/beach/  — Beach VENUE booking."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        req = BeachBookingRequest(data=request.data)
        req.is_valid(raise_exception=True)
        try:
            r = services.create_beach_reservation(user=request.user, **req.validated_data)
        except services.BookingError as exc:
            return _error(exc)
        r = BEACH_QS.get(pk=r.pk)
        return Response({**BeachReservationSerializer(r).data, "worker_pid": os.getpid()},
                        status=status.HTTP_201_CREATED)


class GuideBookingView(APIView):
    """POST /api/bookings/mountain/  — Mountain TOUR-GUIDE booking."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        req = GuideBookingRequest(data=request.data)
        req.is_valid(raise_exception=True)
        try:
            r = services.create_guide_reservation(user=request.user, **req.validated_data)
        except services.BookingError as exc:
            return _error(exc)
        r = GUIDE_QS.get(pk=r.pk)
        return Response({**GuideReservationSerializer(r).data, "worker_pid": os.getpid()},
                        status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------
# Camper: my bookings / history / cancel
# --------------------------------------------------------------------------
class MyBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        st = request.query_params.get("status")
        b, g = BEACH_QS.filter(user=request.user), GUIDE_QS.filter(user=request.user)
        if st in BookingStatus.values:
            b, g = b.filter(status=st), g.filter(status=st)
        return Response(_combined(b, g))


MODELS = {"beach": (BeachReservation, BEACH_QS, BeachReservationSerializer),
          "mountain": (GuideReservation, GUIDE_QS, GuideReservationSerializer)}


class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, kind, pk):
        if kind not in MODELS:
            return Response(status=404)
        model, qs, ser = MODELS[kind]
        r = get_object_or_404(qs, pk=pk)
        if r.user_id != request.user.id:  # users can only touch their own bookings
            raise PermissionDenied("This is not your reservation.")
        if not services.can_user_cancel(r):
            return Response({"detail": "This reservation can no longer be cancelled."}, status=400)
        try:
            services.change_status(model, pk, BookingStatus.CANCELLED, actor=request.user, note="Cancelled by camper")
        except services.BookingError as exc:
            return _error(exc)
        return Response(ser(qs.get(pk=pk)).data)


# --------------------------------------------------------------------------
# Operators & guides: manage own reservations and availability
# --------------------------------------------------------------------------
def _provider_scope(user):
    role = role_of(user)
    if role == Role.ADMIN:
        return BeachVenue.objects.all(), MountainGuide.objects.all()
    venues = BeachVenue.objects.filter(operator=user) if role == Role.VENUE_OPERATOR else BeachVenue.objects.none()
    guides = MountainGuide.objects.filter(user=user) if role == Role.GUIDE else MountainGuide.objects.none()
    return venues, guides


class ProviderServicesView(APIView):
    permission_classes = [IsServiceProvider]

    def get(self, request):
        venues, guides = _provider_scope(request.user)
        return Response({
            "venues": [{"id": v.id, "name": v.name, "destination": v.destination.name} for v in
                       venues.select_related("destination")],
            "guides": [{"id": g.id, "name": g.display_name, "destination": g.destination.name} for g in
                       guides.select_related("destination")],
        })


class ProviderReservationsView(APIView):
    permission_classes = [IsServiceProvider]

    def get(self, request):
        venues, guides = _provider_scope(request.user)
        return Response(_combined(BEACH_QS.filter(slot__venue__in=venues), GUIDE_QS.filter(schedule__guide__in=guides)))


class ReservationStatusView(APIView):
    """Operators/guides approve or reject their own reservations; admins any."""

    permission_classes = [IsServiceProvider]

    def post(self, request, kind, pk):
        if kind not in MODELS:
            return Response(status=404)
        model, qs, ser = MODELS[kind]
        venues, guides = _provider_scope(request.user)
        scoped = qs.filter(slot__venue__in=venues) if kind == "beach" else qs.filter(schedule__guide__in=guides)
        get_object_or_404(scoped, pk=pk)
        req = StatusChangeRequest(data=request.data)
        req.is_valid(raise_exception=True)
        try:
            services.change_status(model, pk, req.validated_data["status"], actor=request.user,
                                   note=req.validated_data["note"])
        except services.BookingError as exc:
            return _error(exc)
        return Response(ser(qs.get(pk=pk)).data)


class _ScopedSlotViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsServiceProvider]
    owner_field = None

    def _owned(self):
        venues, guides = _provider_scope(self.request.user)
        return venues if self.owner_field == "venue" else guides

    def perform_create(self, serializer):
        if serializer.validated_data[self.owner_field] not in self._owned():
            raise PermissionDenied("You can only add availability for your own services.")
        try:
            with transaction.atomic():
                serializer.save()
                realtime.slot_changed(serializer.instance, self.kind)
        except IntegrityError:
            raise ValidationError("This time range overlaps an existing slot.")

    def perform_update(self, serializer):
        owner = serializer.validated_data.get(self.owner_field, getattr(serializer.instance, self.owner_field))
        if owner not in self._owned():
            raise PermissionDenied("You can only edit availability for your own services.")
        try:
            with transaction.atomic():
                serializer.save()
                realtime.slot_changed(serializer.instance, self.kind)
        except IntegrityError:
            raise ValidationError("This time range overlaps an existing slot.")

    def perform_destroy(self, instance):
        if instance.reservations.exists():
            raise ValidationError("Slot has reservations — close it instead of deleting it.")
        instance.delete()


class ProviderVenueSlotViewSet(_ScopedSlotViewSet):
    serializer_class = VenueSlotSerializer
    owner_field = "venue"
    kind = "beach"

    def get_queryset(self):
        return VenueSlot.objects.filter(venue__in=self._owned()).select_related("venue").prefetch_related(
            "reservations")


class ProviderGuideScheduleViewSet(_ScopedSlotViewSet):
    serializer_class = GuideScheduleSerializer
    owner_field = "guide"
    kind = "mountain"

    def get_queryset(self):
        return GuideSchedule.objects.filter(guide__in=self._owned()).select_related("guide").prefetch_related(
            "reservations")


# --------------------------------------------------------------------------
# Admin: all reservations + dashboard stats
# --------------------------------------------------------------------------
class AdminReservationsView(APIView):
    permission_classes = [IsSystemAdmin]

    def get(self, request):
        st = request.query_params.get("status")
        b, g = BEACH_QS.all(), GUIDE_QS.all()
        if st in BookingStatus.values:
            b, g = b.filter(status=st), g.filter(status=st)
        return Response(_combined(b[:300], g[:300]))


class AdminStatsView(APIView):
    permission_classes = [IsSystemAdmin]

    def get(self, request):
        from django.contrib.auth.models import User

        def by_status(qs):
            return {row["status"]: row["n"] for row in qs.values("status").annotate(n=Count("id"))}

        d = Destination.objects.aggregate(
            total=Count("id"), beaches=Count("id", filter=Q(category="BEACH")),
            mountains=Count("id", filter=Q(category="MOUNTAIN")), verified=Count("id", filter=Q(is_verified=True)),
            bookable=Count("id", filter=Q(booking_enabled=True)))
        revenue = (BeachReservation.objects.filter(status__in=["APPROVED", "COMPLETED"]).aggregate(s=Sum("total_amount"))["s"] or 0) + \
                  (GuideReservation.objects.filter(status__in=["APPROVED", "COMPLETED"]).aggregate(s=Sum("total_amount"))["s"] or 0)
        return Response({
            "users": User.objects.count(),
            "destinations": d,
            "beach_reservations": by_status(BeachReservation.objects),
            "guide_reservations": by_status(GuideReservation.objects),
            "venues": BeachVenue.objects.count(), "guides": MountainGuide.objects.count(),
            "open_venue_slots": VenueSlot.objects.filter(is_open=True, start_at__gt=timezone.now()).count(),
            "open_guide_schedules": GuideSchedule.objects.filter(is_open=True, start_at__gt=timezone.now()).count(),
            "simulated_booking_value_php": revenue,
        })


@api_view(["GET"])
@permission_classes([AllowAny])
def system_info(request):
    """Shows which worker process answered — call it repeatedly to see different PIDs."""
    return Response({"worker_pid": os.getpid(), "server_time": timezone.now()})
