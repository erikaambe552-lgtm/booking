from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

provider = DefaultRouter()
provider.register("venue-slots", views.ProviderVenueSlotViewSet, basename="provider-venue-slot")
provider.register("guide-schedules", views.ProviderGuideScheduleViewSet, basename="provider-guide-schedule")

urlpatterns = [
    path("destinations/<slug:slug>/availability/", views.availability),
    path("bookings/beach/", views.BeachBookingView.as_view()),
    path("bookings/mountain/", views.GuideBookingView.as_view()),
    path("bookings/mine/", views.MyBookingsView.as_view()),
    path("bookings/<str:kind>/<int:pk>/cancel/", views.CancelBookingView.as_view()),
    path("operator/services/", views.ProviderServicesView.as_view()),
    path("operator/reservations/", views.ProviderReservationsView.as_view()),
    path("operator/reservations/<str:kind>/<int:pk>/status/", views.ReservationStatusView.as_view()),
    path("operator/", include(provider.urls)),
    path("admin/reservations/", views.AdminReservationsView.as_view()),
    path("admin/reservations/<str:kind>/<int:pk>/status/", views.ReservationStatusView.as_view()),
    path("admin/stats/", views.AdminStatsView.as_view()),
    path("system/info/", views.system_info),
]
