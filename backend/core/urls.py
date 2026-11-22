from django.urls import include, path

urlpatterns = [
    path("auth/", include("core.accounts.urls")),
    path("", include("core.destinations.urls")),
    path("", include("core.bookings.urls")),
]
