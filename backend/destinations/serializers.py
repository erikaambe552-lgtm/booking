from rest_framework import serializers

from .models import BeachVenue, Category, Destination, DestinationImage, MountainGuide


class DestinationImageSerializer(serializers.ModelSerializer):
    src = serializers.CharField(read_only=True)
    credit_line = serializers.CharField(read_only=True)

    class Meta:
        model = DestinationImage
        fields = ["id", "destination", "src", "image_file", "image_url", "caption", "credit", "license",
                  "source_page", "credit_line", "is_cover", "order"]
        extra_kwargs = {"image_file": {"write_only": True, "required": False},
                        "image_url": {"required": False}}

    def validate_credit(self, v):
        if not v.strip():
            raise serializers.ValidationError("A photo credit is required.")
        return v

    def validate(self, attrs):
        if not attrs.get("image_file") and not attrs.get("image_url") and not self.instance:
            raise serializers.ValidationError("Upload a photo file or provide an image URL.")
        return attrs


class PublicVenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeachVenue
        fields = ["id", "name", "description", "max_guests", "base_price", "price_per_extra_guest",
                  "included_guests", "amenities", "is_demo"]


class PublicGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = MountainGuide
        fields = ["id", "display_name", "bio", "max_participants", "price_per_group", "price_per_participant",
                  "accreditation", "is_demo"]


class DestinationListSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    is_bookable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Destination
        fields = ["id", "name", "slug", "category", "province", "municipality", "barangay", "location_verified",
                  "location_note", "short_description", "cover_image", "is_bookable", "is_featured", "is_verified"]

    def get_cover_image(self, obj):
        imgs = list(obj.images.all())  # prefetched
        if not imgs:
            return None
        img = next((i for i in imgs if i.is_cover), imgs[0])
        return {"url": img.src, "credit": img.credit_line, "caption": img.caption}


class DestinationDetailSerializer(DestinationListSerializer):
    images = DestinationImageSerializer(many=True, read_only=True)
    services = serializers.SerializerMethodField()

    class Meta(DestinationListSerializer.Meta):
        fields = DestinationListSerializer.Meta.fields + [
            "description", "amenities", "activities", "reservation_instructions", "latitude", "longitude",
            "images", "services", "booking_enabled",
        ]

    def get_services(self, obj):
        # Only verified, active, admin-configured services are ever shown.
        if obj.category == Category.BEACH:
            qs = obj.venues.filter(is_active=True, is_verified=True)
            return {"type": "VENUE", "items": PublicVenueSerializer(qs, many=True).data}
        qs = obj.guides.filter(is_active=True, is_verified=True)
        return {"type": "GUIDE", "items": PublicGuideSerializer(qs, many=True).data}


# ---------------- admin serializers ----------------
class AdminDestinationSerializer(serializers.ModelSerializer):
    is_bookable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Destination
        fields = "__all__"
        read_only_fields = ["slug", "province", "created_at", "updated_at"]

    def validate(self, attrs):
        verified = attrs.get("is_verified", getattr(self.instance, "is_verified", False))
        enabled = attrs.get("booking_enabled", getattr(self.instance, "booking_enabled", False))
        if enabled and not verified:
            raise serializers.ValidationError("Verify the destination before enabling bookings.")
        for key in ("amenities", "activities"):
            if key in attrs and not (isinstance(attrs[key], list) and all(isinstance(x, str) for x in attrs[key])):
                raise serializers.ValidationError({key: "Must be a list of text items."})
        return attrs


class AdminVenueSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)

    class Meta:
        model = BeachVenue
        fields = "__all__"

    def validate_destination(self, d):
        if d.category != Category.BEACH:
            raise serializers.ValidationError("Venues belong to beach destinations only.")
        return d


class AdminGuideSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)

    class Meta:
        model = MountainGuide
        fields = "__all__"

    def validate_destination(self, d):
        if d.category != Category.MOUNTAIN:
            raise serializers.ValidationError("Tour guides belong to mountain destinations only.")
        return d
