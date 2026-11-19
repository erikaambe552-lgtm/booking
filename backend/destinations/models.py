"""Destination catalog — strictly Biliran Province only.

Beach inventory (BeachVenue) and mountain inventory (MountainGuide) are kept in
separate tables so the two reservation workflows never share records.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Municipality(models.TextChoices):
    # The 8 municipalities of Biliran Province. Nothing outside this list is accepted.
    ALMERIA = "Almeria", "Almeria"
    BILIRAN = "Biliran", "Biliran"
    CABUCGAYAN = "Cabucgayan", "Cabucgayan"
    CAIBIRAN = "Caibiran", "Caibiran"
    CULABA = "Culaba", "Culaba"
    KAWAYAN = "Kawayan", "Kawayan"
    MARIPIPI = "Maripipi", "Maripipi"
    NAVAL = "Naval", "Naval"


class Category(models.TextChoices):
    BEACH = "BEACH", "Beach"
    MOUNTAIN = "MOUNTAIN", "Mountain"


PROVINCE = "Biliran"


class Destination(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    category = models.CharField(max_length=10, choices=Category.choices)
    province = models.CharField(max_length=40, default=PROVINCE, editable=False)
    municipality = models.CharField(max_length=20, choices=Municipality.choices, blank=True,
                                    help_text="Leave blank until the municipality is verified.")
    barangay = models.CharField(max_length=120, blank=True)
    location_verified = models.BooleanField(default=False)
    location_note = models.CharField(max_length=300, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    short_description = models.CharField(max_length=280)
    description = models.TextField(blank=True)
    amenities = models.JSONField(default=list, blank=True)
    activities = models.JSONField(default=list, blank=True)
    reservation_instructions = models.TextField(blank=True)
    source_notes = models.TextField(blank=True, help_text="Where the information was verified (for admins).")

    is_published = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False, help_text="Information checked by an administrator.")
    booking_enabled = models.BooleanField(default=False, help_text="Only admins can enable bookings.")
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0, help_text="Display order on the homepage/explore page.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "sort_order", "name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(province=PROVINCE), name="destination_biliran_only"),
            # A destination can only take bookings once it is verified.
            models.CheckConstraint(
                condition=models.Q(booking_enabled=False) | models.Q(is_verified=True),
                name="booking_requires_verification",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.province != PROVINCE:
            raise ValidationError("CampBlazer only lists destinations in Biliran Province.")
        if self.municipality and self.municipality not in Municipality.values:
            raise ValidationError({"municipality": "Must be one of Biliran's 8 municipalities."})
        if self.booking_enabled and not self.is_verified:
            raise ValidationError("Verify the destination before enabling bookings.")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.province = PROVINCE
        super().save(*args, **kwargs)

    @property
    def is_bookable(self):
        if not (self.is_published and self.is_verified and self.booking_enabled):
            return False
        # Iterates .all() so a prefetch_related("venues", "guides") avoids N+1 queries.
        services = self.venues.all() if self.category == Category.BEACH else self.guides.all()
        return any(s.is_active and s.is_verified for s in services)


def validate_image_file(f):
    ext = f.name.rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise ValidationError("Upload a JPG, PNG or WEBP photo.")
    if f.size > 8 * 1024 * 1024:
        raise ValidationError("Photo must be 8 MB or smaller.")


class DestinationImage(models.Model):
    """Authentic, licensed destination photos ONLY.
    Either upload a file (team's own photo / photo used with permission) or link
    an image URL (e.g. a Wikimedia Commons file under a free licence).
    A credit is always required and is displayed on the site."""

    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="images")
    image_file = models.FileField(upload_to="destinations/", blank=True, validators=[validate_image_file])
    image_url = models.URLField(max_length=500, blank=True)
    caption = models.CharField(max_length=200, blank=True)
    credit = models.CharField(max_length=200, help_text="Photographer / owner. Required.")
    license = models.CharField(max_length=120, blank=True, help_text="e.g. CC BY-SA 4.0, 'Used with permission', 'Own photo'")
    source_page = models.URLField(max_length=500, blank=True, help_text="Where the licence can be checked.")
    is_cover = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-is_cover", "order", "id"]
        constraints = [
            models.CheckConstraint(condition=~models.Q(image_file="") | ~models.Q(image_url=""),
                                   name="image_has_file_or_url"),
        ]

    def __str__(self):
        return f"{self.destination} — {self.caption or self.src}"

    @property
    def src(self):
        return self.image_file.url if self.image_file else self.image_url

    @property
    def credit_line(self):
        return " · ".join(x for x in (self.credit, self.license) if x)


class BeachVenue(models.Model):
    """A bookable venue / cottage / camping area at a BEACH destination."""

    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="venues",
                                    limit_choices_to={"category": Category.BEACH})
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="operated_venues")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    max_guests = models.PositiveSmallIntegerField(default=10)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="PHP per booking slot")
    price_per_extra_guest = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    included_guests = models.PositiveSmallIntegerField(default=1)
    amenities = models.JSONField(default=list, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False, help_text="Simulated record for demos/testing.")

    class Meta:
        ordering = ["destination", "name"]
        constraints = [
            # Prevents duplicate inventory for the same venue at the same destination.
            models.UniqueConstraint(fields=["destination", "name"], name="uniq_venue_per_destination"),
            models.CheckConstraint(condition=models.Q(max_guests__gte=1), name="venue_max_guests_positive"),
        ]

    def __str__(self):
        return f"{self.name} @ {self.destination.name}"

    def clean(self):
        if self.destination_id and self.destination.category != Category.BEACH:
            raise ValidationError("Venues can only be attached to beach destinations.")


class MountainGuide(models.Model):
    """A tour guide / guided service for a MOUNTAIN destination."""

    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="guides",
                                    limit_choices_to={"category": Category.MOUNTAIN})
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="guide_profiles")
    display_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    max_participants = models.PositiveSmallIntegerField(default=8)
    price_per_group = models.DecimalField(max_digits=10, decimal_places=2, help_text="PHP guide fee per tour")
    price_per_participant = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    accreditation = models.CharField(max_length=200, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False, help_text="Simulated record for demos/testing.")

    class Meta:
        ordering = ["destination", "display_name"]
        constraints = [
            models.UniqueConstraint(fields=["destination", "display_name"], name="uniq_guide_per_destination"),
        ]

    def __str__(self):
        return f"{self.display_name} — {self.destination.name}"

    def clean(self):
        if self.destination_id and self.destination.category != Category.MOUNTAIN:
            raise ValidationError("Tour guides can only be attached to mountain destinations.")
