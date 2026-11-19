from django.contrib import admin

from .models import BeachReservation, BookingHistory, GuideReservation, GuideSchedule, VenueSlot


@admin.register(BeachReservation, GuideReservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "status", "total_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("reference", "user__username", "customer_name")


admin.site.register(VenueSlot)
admin.site.register(GuideSchedule)
admin.site.register(BookingHistory)
