from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import AdminUserViewSet

from .views import (AdminDestinationViewSet, AdminGuideViewSet, AdminImageViewSet, AdminVenueViewSet,
                    DestinationViewSet, municipalities)

public = DefaultRouter()
public.register("destinations", DestinationViewSet, basename="destination")

admin = DefaultRouter()
admin.register("users", AdminUserViewSet, basename="admin-user")
admin.register("destinations", AdminDestinationViewSet, basename="admin-destination")
admin.register("images", AdminImageViewSet, basename="admin-image")
admin.register("venues", AdminVenueViewSet, basename="admin-venue")
admin.register("guides", AdminGuideViewSet, basename="admin-guide")

urlpatterns = [
    path("municipalities/", municipalities),
    path("", include(public.urls)),
    path("admin/", include(admin.urls)),
]
