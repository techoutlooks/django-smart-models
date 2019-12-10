# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from oauth2_provider.models import AccessToken
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class OAuthError(RuntimeError):
    """
    OAuth exception class
    """
    def __init__(self, message='OAuth error occured.'):
        self.message = message


class IsAuthenticated(permissions.BasePermission):

    def has_permission(self, request, view):
        return self.is_authenticated(request)

    def is_authenticated(self, request, **kwargs):
        """
        Authenticates a two legged Oauth2 request
        """
        # TODO: request.META['token'] expects token!

        try:
            key = None
            auth_header_value = request.META.get('HTTP_AUTHORIZATION')
            if auth_header_value:
                key = auth_header_value.split(' ')[1]
            if not key:
                logging.error('OAuth20Authentication. No consumer_key found.')
                return False

            # Set the request user to the token user for authorization if Oauth is successful
            token = self.validate_token(key, request.user)
            request.user = token.user

            # Also set oauth_consumer_key on request.
            request.META['token'] = key

        except KeyError as e:
            logging.exception("Error in OAuth20Authentication.")
            request.user = AnonymousUser()
            return False
        except Exception as e:
            logging.exception("Error in OAuth20Authentication.")
            return False

        # Oauth successfull! Yay!
        return True

    def validate_token(self, key, user):
        """
        Raise proper exception is token key is invalid
        """
        try:
            token = AccessToken.objects.get(token=key)

            if token.expires < timezone.now():
                raise OAuthError('AccessToken has expired.')
        except AccessToken.DoesNotExist as e:
            raise OAuthError("AccessToken not found at all.")

        logging.info('auth token validation check successful for user {user}'.format(user=user))
        return token


class IsReadOnly(IsAuthenticated):
    def has_permission(self, request, view):
        perms = super(IsReadOnly, self).has_permission(request, view)
        return bool(
            perms and
            request.method in permissions.SAFE_METHODS
        )
