# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsAuthenticatedOrCreate(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return True
        return super(IsAuthenticatedOrCreate, self).has_permission(request, view)


class IsOwner(permissions.IsAuthenticated):
    """
    Permission that requires the logged in owner to have `ownership` of the object he is accessing,
    ie., must have created that object; unless the obj is being created.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated:
            return (request.user == obj.created_by) or (request.user == obj.owner)
        return False


class IsAdminOrIsOwner(IsOwner):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or \
               super(IsAdminOrIsOwner, self).has_object_permission(request, view, obj)


class SSLPermission(BasePermission):  # pragma: no cover
    def has_permission(self, request, view):
        if getattr(settings, 'SESSION_COOKIE_SECURE', False):
            return request.is_secure()
        else:
            return True


class IsReadOnly(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        perms = super(IsReadOnly, self).has_permission(request, view)
        return bool(
            perms and
            request.method in permissions.SAFE_METHODS
        )
