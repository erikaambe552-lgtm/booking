"""Availability and reservation records.

Two completely separate inventories:
  * Beaches   -> VenueSlot      -> BeachReservation   (venue booking)
  * Mountains -> GuideSchedule  -> GuideReservation   (tour-guide booking)

Database-level guarantees (PostgreSQL), independent of application code:
  1. ExclusionConstraint: a venue (or guide) can never have two OVERLAPPING
     slots/schedules.
  2. Partial UniqueConstraint: a slot/schedule can hold at most ONE active
     (PENDING or APPROVED) reservation — i.e. it is an exclusive resource.
Even if two workers somehow bypassed the row lock, the second INSERT would be
rejected with an IntegrityError.
"""
import secrets

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Func, Q

from destinations.models import BeachVenue, MountainGuide


class TsTzRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


ACTIVE_STATUSES = [BookingStatus.PENDING, BookingStatus.APPROVED]


def new_reference(prefix):
    return f"{prefix}-{secrets.token_hex(4).upper()}"


# --------------------------------------------------------------------------
# Availability (shared resources)
# --------------------------------------------------------------------------
class VenueSlot(models.Model):
    venue = models.ForeignKey(BeachVenue, on_delete=models.CASCADE, related_name="slots")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_open = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_at"]
        constraints = [
            models.CheckConstraint(condition=Q(end_at__gt=F("start_at")), name="venueslot_end_after_start"),
            ExclusionConstraint(
                name="venueslot_no_overlap",
                expressions=[
                    (TsTzRange("start_at", "end_at", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("venue", RangeOperators.EQUAL),
                ],
            ),
        ]

    def __str__(self):
        return f"{self.venue} | {self.start_at:%Y-%m-%d %H:%M}-{self.end_at:%H:%M}"


class GuideSchedule(models.Model):
    guide = models.ForeignKey(MountainGuide, on_delete=models.CASCADE, related_name="schedules")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    meeting_point = models.CharField(max_length=200, blank=True)
    is_open = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_at"]
        constraints = [
            models.CheckConstraint(condition=Q(end_at__gt=F("start_at")), name="guideschedule_end_after_start"),
            ExclusionConstraint(
                name="guideschedule_no_overlap",
                expressions=[
                    (TsTzRange("start_at", "end_at", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("guide", RangeOperators.EQUAL),
                ],
            ),
        ]

    def __str__(self):
        return f"{self.guide} | {self.start_at:%Y-%m-%d %H:%M}"


# --------------------------------------------------------------------------
# Reservations
# --------------------------------------------------------------------------
class ReservationBase(models.Model):
    reference = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="%(class)ss")
    customer_name = models.CharField(max_length=150)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()
    special_requests = models.TextField(blank=True, max_length=1000)
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    extra_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REF_PREFIX = "CB"

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = new_reference(self.REF_PREFIX)
        super().save(*args, **kwargs)


class BeachReservation(ReservationBase):
    REF_PREFIX = "CBB"
    slot = models.ForeignKey(VenueSlot, on_delete=models.PROTECT, related_name="reservations")
    guests = models.PositiveSmallIntegerField()

    class Meta(ReservationBase.Meta):
        constraints = [
            models.UniqueConstraint(fields=["slot"], condition=Q(status__in=ACTIVE_STATUSES),
                                    name="one_active_reservation_per_venue_slot"),
            models.CheckConstraint(condition=Q(guests__gte=1), name="beach_guests_positive"),
        ]

    def __str__(self):
        return f"{self.reference} ({self.status})"


class GuideReservation(ReservationBase):
    REF_PREFIX = "CBM"
    schedule = models.ForeignKey(GuideSchedule, on_delete=models.PROTECT, related_name="reservations")
    participants = models.PositiveSmallIntegerField()

    class Meta(ReservationBase.Meta):
        constraints = [
            models.UniqueConstraint(fields=["schedule"], condition=Q(status__in=ACTIVE_STATUSES),
                                    name="one_active_reservation_per_guide_schedule"),
            models.CheckConstraint(condition=Q(participants__gte=1), name="guide_participants_positive"),
        ]

    def __str__(self):
        return f"{self.reference} ({self.status})"


class BookingHistory(models.Model):
    """Audit trail of every status change (who, when, from -> to)."""

    beach_reservation = models.ForeignKey(BeachReservation, null=True, blank=True, on_delete=models.CASCADE,
                                          related_name="history")
    guide_reservation = models.ForeignKey(GuideReservation, null=True, blank=True, on_delete=models.CASCADE,
                                          related_name="history")
    from_status = models.CharField(max_length=10, blank=True)
    to_status = models.CharField(max_length=10, choices=BookingStatus.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "booking history"
        constraints = [
            models.CheckConstraint(
                condition=(Q(beach_reservation__isnull=False, guide_reservation__isnull=True)
                           | Q(beach_reservation__isnull=True, guide_reservation__isnull=False)),
                name="history_exactly_one_reservation",
            )
        ]
