import logging

from django.conf import settings
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


class IsOwner(permissions.BasePermission):
    """
    Permission that requires a user to have ownership of the object he is accessing,
     ie. he must have created that object.
    """

    def has_object_permission(self, request, view, obj):
        # if self.is_authenticated(request):
        if request.user.is_authenticated():
            return request.user == obj.created_by

    # def has_permission(self, request, view):
    #     return self.is_authenticated(request)

    def is_authenticated(self, request, **kwargs):
        """
        Authenticates a two legged Oauth request
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
            token = self.verify_token(key)
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

    def verify_token(self, key):
        """
        Raise proper exception is token key is invalid
        """
        try:
            token = AccessToken.objects.get(token=key)

            if token.expires < timezone.now():
                raise OAuthError('AccessToken has expired.')
        except AccessToken.DoesNotExist as e:
            raise OAuthError("AccessToken not found at all.")

        logging.info('Valid access')
        return token


class IsAdminOrIsOwner(IsOwner):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or \
               super().has_object_permission(request, view, obj)


class IsAccountValid(permissions.BasePermission):
    """
    Deny requests send by a user whose account has issues:

    - deny any requests unless account is is_verified
    - deny any requests unless account has not expired

    """
    def has_object_permission(self, request, view, obj):
        """
        Unless POST (account creation, passcode reset), check if:
        the user account is is_verified, has not expired.
        """
        if request.method == 'POST':
            return True

        # `has_object_permission1 is only run if has_permission()=True
        # this ensures that a valid user is always available.
        account = request.user.account
        return account.is_verified and not account.has_expired


class SSLPermission(BasePermission):  # pragma: no cover
    def has_permission(self, request, view):
        if getattr(settings, 'SESSION_COOKIE_SECURE', False):
            return request.is_secure()
        else:
            return True
