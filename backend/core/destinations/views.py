from django.db.models import Prefetch, ProtectedError, Q
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.accounts.permissions import IsSystemAdmin

from .models import BeachVenue, Category, Destination, DestinationImage, MountainGuide, Municipality
from .serializers import (AdminDestinationSerializer, AdminGuideSerializer, AdminVenueSerializer,
                          DestinationDetailSerializer, DestinationImageSerializer, DestinationListSerializer)


class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """Public catalog. Filters: ?category=BEACH|MOUNTAIN  ?municipality=Naval  ?q=search  ?featured=1"""

    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        qs = (Destination.objects.filter(is_published=True)
              .prefetch_related(Prefetch("images", queryset=DestinationImage.objects.all()), "venues", "guides"))
        p = self.request.query_params
        if p.get("category") in Category.values:
            qs = qs.filter(category=p["category"])
        if p.get("municipality") in Municipality.values:
            qs = qs.filter(municipality=p["municipality"])
        if p.get("q"):
            q = p["q"].strip()[:80]
            qs = qs.filter(Q(name__icontains=q) | Q(short_description__icontains=q) | Q(barangay__icontains=q)
                           | Q(municipality__icontains=q))
        if p.get("featured") == "1":
            qs = qs.filter(is_featured=True)
        return qs

    def get_serializer_class(self):
        return DestinationDetailSerializer if self.action == "retrieve" else DestinationListSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def municipalities(request):
    return Response([{"value": v, "label": l} for v, l in Municipality.choices])


class SafeDeleteMixin:
    """Refuse to delete records that still have reservations (history must be kept)."""

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("This record has reservations. Disable it instead of deleting it.")


class AdminDestinationViewSet(SafeDeleteMixin, viewsets.ModelViewSet):
    permission_classes = [IsSystemAdmin]
    serializer_class = AdminDestinationSerializer
    queryset = Destination.objects.all().prefetch_related("venues", "guides")

    def perform_create(self, serializer):
        instance = serializer.save()
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("destinations", "created", instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("destinations", "updated", instance.id)

    def perform_destroy(self, instance):
        record_id = instance.id
        super().perform_destroy(instance)
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("destinations", "deleted", record_id)


class AdminImageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSystemAdmin]
    serializer_class = DestinationImageSerializer

    def get_queryset(self):
        qs = DestinationImage.objects.all()
        d = self.request.query_params.get("destination")
        return qs.filter(destination_id=d) if d else qs

    def perform_create(self, serializer):
        instance = serializer.save()
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("destinations", "image-created", instance.destination_id)

    def perform_destroy(self, instance):
        destination_id = instance.destination_id
        instance.delete()
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("destinations", "image-deleted", destination_id)


class AdminVenueViewSet(SafeDeleteMixin, viewsets.ModelViewSet):
    permission_classes = [IsSystemAdmin]
    serializer_class = AdminVenueSerializer
    queryset = BeachVenue.objects.select_related("destination")

    def perform_create(self, serializer):
        instance = serializer.save()
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("services", "created", instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("services", "updated", instance.id)

    def perform_destroy(self, instance):
        record_id = instance.id
        super().perform_destroy(instance)
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("services", "deleted", record_id)


class AdminGuideViewSet(SafeDeleteMixin, viewsets.ModelViewSet):
    permission_classes = [IsSystemAdmin]
    serializer_class = AdminGuideSerializer
    queryset = MountainGuide.objects.select_related("destination")

    def perform_create(self, serializer):
        instance = serializer.save()
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("services", "created", instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("services", "updated", instance.id)

    def perform_destroy(self, instance):
        record_id = instance.id
        super().perform_destroy(instance)
        from core.bookings.realtime import admin_data_changed
        admin_data_changed("services", "deleted", record_id)
