from typing import Any

from rest_framework import permissions

from .requests import AuthenticatedRequest


class IsOwner(permissions.IsAuthenticated):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request: AuthenticatedRequest, view: Any, obj: Any):
        if isinstance(obj, request.user.__class__):
            return obj == request.user

        if hasattr(obj, "user"):
            return obj.user == request.user

        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit.
    """

    def has_object_permission(self, request: AuthenticatedRequest, view: Any, obj: Any):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        if isinstance(obj, request.user.__class__):
            return obj == request.user

        if hasattr(obj, "user"):
            return obj.user == request.user

        return False
