from rest_framework import serializers

from .models import BeachReservation, BookingHistory, GuideReservation, GuideSchedule, VenueSlot
from .services import can_user_cancel

PHONE_RE = r"^[0-9+\- ]{7,20}$"


class _CustomerFields(serializers.Serializer):
    customer_name = serializers.CharField(max_length=150)
    contact_phone = serializers.RegexField(PHONE_RE)
    contact_email = serializers.EmailField()
    special_requests = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class BeachBookingRequest(_CustomerFields):
    slot_id = serializers.IntegerField(min_value=1)
    guests = serializers.IntegerField(min_value=1, max_value=500)


class GuideBookingRequest(_CustomerFields):
    schedule_id = serializers.IntegerField(min_value=1)
    participants = serializers.IntegerField(min_value=1, max_value=100)


class HistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.CharField(source="changed_by.username", default=None)

    class Meta:
        model = BookingHistory
        fields = ["from_status", "to_status", "changed_by", "note", "created_at"]


class BeachReservationSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    destination = serializers.CharField(source="slot.venue.destination.name")
    destination_slug = serializers.CharField(source="slot.venue.destination.slug")
    service = serializers.CharField(source="slot.venue.name")
    start_at = serializers.DateTimeField(source="slot.start_at")
    end_at = serializers.DateTimeField(source="slot.end_at")
    party_size = serializers.IntegerField(source="guests")
    can_cancel = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username")
    history = HistorySerializer(many=True, read_only=True)

    class Meta:
        model = BeachReservation
        fields = ["id", "type", "reference", "status", "destination", "destination_slug", "service", "start_at",
                  "end_at", "party_size", "customer_name", "contact_phone", "contact_email", "special_requests",
                  "base_amount", "extra_amount", "total_amount", "created_at", "can_cancel", "username", "history"]

    def get_type(self, obj):
        return "BEACH"

    def get_can_cancel(self, obj):
        return can_user_cancel(obj)


class GuideReservationSerializer(BeachReservationSerializer):
    destination = serializers.CharField(source="schedule.guide.destination.name")
    destination_slug = serializers.CharField(source="schedule.guide.destination.slug")
    service = serializers.CharField(source="schedule.guide.display_name")
    start_at = serializers.DateTimeField(source="schedule.start_at")
    end_at = serializers.DateTimeField(source="schedule.end_at")
    party_size = serializers.IntegerField(source="participants")
    meeting_point = serializers.CharField(source="schedule.meeting_point")

    class Meta(BeachReservationSerializer.Meta):
        model = GuideReservation
        fields = BeachReservationSerializer.Meta.fields + ["meeting_point"]

    def get_type(self, obj):
        return "MOUNTAIN"


class VenueSlotSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source="venue.name", read_only=True)
    available = serializers.SerializerMethodField()

    class Meta:
        model = VenueSlot
        fields = ["id", "venue", "venue_name", "start_at", "end_at", "is_open", "note", "available"]

    def get_available(self, obj):
        return obj.is_open and not any(r.status in ("PENDING", "APPROVED") for r in obj.reservations.all())

    def validate(self, attrs):
        s, e = attrs.get("start_at", getattr(self.instance, "start_at", None)), attrs.get(
            "end_at", getattr(self.instance, "end_at", None))
        if s and e and e <= s:
            raise serializers.ValidationError("End time must be after start time.")
        return attrs


class GuideScheduleSerializer(VenueSlotSerializer):
    guide_name = serializers.CharField(source="guide.display_name", read_only=True)
    venue_name = None

    class Meta:
        model = GuideSchedule
        fields = ["id", "guide", "guide_name", "start_at", "end_at", "meeting_point", "is_open", "note",
                  "available"]


class StatusChangeRequest(serializers.Serializer):
    status = serializers.ChoiceField(choices=["APPROVED", "REJECTED", "CANCELLED", "COMPLETED"])
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
