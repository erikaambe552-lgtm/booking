from django.contrib import admin

from .models import BeachVenue, Destination, DestinationImage, MountainGuide


class ImageInline(admin.TabularInline):
    model = DestinationImage
    extra = 0


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "municipality", "location_verified", "is_verified", "booking_enabled")
    list_filter = ("category", "municipality", "is_verified", "booking_enabled")
    search_fields = ("name",)
    inlines = [ImageInline]


admin.site.register(BeachVenue)
admin.site.register(MountainGuide)
