"""
EpitopX — custom DRF permission classes.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrAdmin(BasePermission):
    """Allow access only to the object owner or an admin user."""

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_admin:
            return True
        owner = getattr(obj, 'created_by', None) or getattr(obj, 'user', None)
        return owner == request.user


class IsAdminUser(BasePermission):
    """Allow access only to users with is_admin=True."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsOwnerOrAdminOrReadOnly(BasePermission):
    """
    Safe methods are allowed to any authenticated user.
    Unsafe methods are restricted to the object owner or admin.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_admin:
            return True
        owner = getattr(obj, 'created_by', None) or getattr(obj, 'user', None)
        return owner == request.user
