from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


def role_of(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return Role.ADMIN
    profile = getattr(user, "profile", None)
    return profile.role if profile else Role.CAMPER


class IsSystemAdmin(BasePermission):
    message = "Administrator access required."

    def has_permission(self, request, view):
        return role_of(request.user) == Role.ADMIN


class IsVenueOperator(BasePermission):
    def has_permission(self, request, view):
        return role_of(request.user) in (Role.VENUE_OPERATOR, Role.ADMIN)


class IsGuide(BasePermission):
    def has_permission(self, request, view):
        return role_of(request.user) in (Role.GUIDE, Role.ADMIN)


class IsServiceProvider(BasePermission):
    message = "Only venue operators, tour guides or administrators can do this."

    def has_permission(self, request, view):
        return role_of(request.user) in (Role.VENUE_OPERATOR, Role.GUIDE, Role.ADMIN)


class ReadOnlyOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or role_of(request.user) == Role.ADMIN
