from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from oauth2_provider.contrib.rest_framework import permissions, TokenHasReadWriteScope
from rest_framework.viewsets import ModelViewSet

from ...models import get_sentinel_user
from .mixins import PrivateResourceViewMixin, SubscribedResourceViewMixin
from ...settings import get_setting
from ..serializers import SmartOwnerSerializer, SmartUserSerializer

from ..permissions import IsAdminOrIsOwner, IsAccountValid

from ...models import get_namespace_model, get_default_namespace, Namespace


ALL_FIELDS = '__all__'


class SmartModelViewSet(ModelViewSet):
    """
    Base class for all other smart views.
    Ensures that all smart fields are correctly set on the SmartView instances
     whether update or creation.
     Eg. a resource's `namespaces`, creator, and update times are set automatically.

    Will raise an exception if `SMART_MODELS_DEFAULT_REQUIRED==True` and the smart
     fields were not supplied in the request by the API user (default behaviour).
    """

    def perform_create(self, serializer):
        smart_fields = self.prepare_smart_fields(fields=('created_by', 'updated_by'),
                                                 serializer=serializer, created=True)
        serializer.save(**smart_fields)

    def perform_update(self, serializer):
        smart_fields = self.prepare_smart_fields(fields=('updated_by',),
                                                 serializer=serializer, updated=True)
        serializer.save(**smart_fields)

    def perform_destroy(self, instance):
        smart_fields = self.prepare_smart_fields(fields=('deleted_by'),
                                                 instance=instance, deleted=True)
        instance.save(**smart_fields)
        instance.delete()

    def get_smart_fields(self, **kwargs):
        # created_at, updated_at, deleted_at already set by the ORM,
        # Cf. AbstractSmartModel definition.
        user = self.get_smart_user(**kwargs) or get_sentinel_user()
        smart_fields = {
            'user': user,
            'created_by': user,
            'updated_by': user,
            'deleted_by': user
        }

        return smart_fields

    def prepare_smart_fields(self, fields=None, exclude=None, **kwargs):
        """
        Prepare a dict of smart fields
        :param update_fields: subset (string iterable) of the smart fields to only care about.
        :return: smart fields dict.
        """
        # TODO: also save smarts of nested fields?
        if fields and fields != ALL_FIELDS and not isinstance(fields, (list, tuple)):
            raise TypeError(
                'The `fields` option must be a list or tuple or "__all__". '
                'Got %s.' % type(fields).__name__
            )

        assert not (fields and exclude), (
            "The `fields` and `exclude` options can't be both set at once,"
            "Nor can't they be both set to `__all_`."
            "Not setting them (None value) is equivalent to `__all__`."
        )
        assert not (exclude == ALL_FIELDS), (
            "All fields can't be excluded at once."
        )

        update_fields = []
        smart_fields = self.get_smart_fields(**kwargs)
        # None eq. __all__
        if not fields or fields == ALL_FIELDS:
            return smart_fields

        if fields:
            update_fields = set(fields) & set(smart_fields)

        if exclude:
            update_fields = set(smart_fields) - set(list(update_fields))

        return {f: smart_fields[f] for f in update_fields}

    def get_smart_model(self):
        return self.get_serializer_class().Meta.model

    def get_smart_user(self, **kwargs):
        """
        Get the active user (optimally from the HTTP session),
        ie. the one responsible for the ongoing operation.
        """

        # except delete ops, we don't like to assume that the currently acting user
        # is as told by the user, that's not secure!
        instance = kwargs.pop('instance', None)
        created = kwargs.pop('created', None)

        # best case, get user from session
        if not self.request.user.is_anonymous:
            return self.request.user

        # is create ops,
        # let's try fetching existing user from data at hand
        if created:
            validated_data = kwargs.pop('serializer').validated_data
            user_serializer = SmartUserSerializer(data=validated_data.get('user', None))
            user_serializer.is_valid()
            return get_user_model()(**user_serializer.validated_data)


class NamespaceViewSet(SmartModelViewSet):
    """
    Read-only. List all contribution domains (`namespaces`) a registering user is susceptible to subscribe to.
     This is the default workflow, as `SMART_MODELS_OWNER_MODEL==Namespace` by design.
    If (planned exception) the User model emulates the contrib domain model, ie. users truly own objects,
     (`SMART_MODELS_OWNER_MODEL==AUTH_USER_MODEL`), we assign ownership of all created objects to the designed
     list of default users (the builtin defaults to the sentinel user as a singleton queryset).

    To supply your own list of designed default namespaces, override static method `get_default_owners()` below.

    """
    serializer_class = SmartOwnerSerializer
    queryset = get_namespace_model().objects.all()

    def get_queryset(self):
        if get_setting('OWNER_MODEL') == settings.AUTH_USER_MODEL:
            return self.get_default_owners()
        return super(NamespaceViewSet, self).get_queryset()

    @staticmethod
    def get_default_owners():
        """
        Builtin implementation defaults a singleton: the `sentinel` instance,
        of the loaded smart model configured through the setting `SMART_MODELS_OWNER_MODEL`.
        """
        return get_default_namespace()


class SharedResourceViewSet(SmartModelViewSet):
    """
    SmartViewSet that
    Although if the objects proprietorship mode is emulated, assumes that the sentinel user is proprietary.
    """

    def get_smart_fields(self):
        smart_fields = super(SharedResourceViewSet, self).get_smart_fields()
        smart_fields.update({
            'namespaces': self.get_smart_owners(),
        })
        return smart_fields

    def get_smart_owners(self):
        """
        Domains (Namespace) the current resource (`self.get_object()`) belongs to.
        On the resource's creation, the namespaces-domains will default to the current user's namespaces-domains,
         unless the user-creator is requesting to set them to some specific (existing) values.
        If the logged in user has no namespace set, namespaces defaults to the builtins set by
         `get_default_namespace()` via the pre_save signal.

        """

        # return the namespaces-domains the request is asking to set,
        # provided they are valid (existed, model validation succeeded, etc.)
        owners_serializer = SmartOwnerSerializer(data=self.request.data, many=True)

        # or return the default
        if not owners_serializer.is_valid():

            owners = get_namespace_model.objects.filter(users=self.request.user)
            owners_serializer = SmartOwnerSerializer(owners, many=True)

        owners_serializer.save()


class PrivateResourceViewSet(PrivateResourceViewMixin, SmartModelViewSet):
    """
    Overrides for displaying the currently logged in user's private resources only.
    In case of multiple inheritance, always place on the left-most side, to ensure
    that a user's private resources are never disclosed to others.

     Eg.
     `
        class AccountEndpoint(PrivateResourceViewSet, SmartViewMixin, ModelViewSet):
            pass
     `
    """
    pass


class SubscribedResourceViewSet(SubscribedResourceViewMixin, SharedResourceViewSet):
    """
    SmartViewSet that displays the resources the currently logged in user is subscribed to.
    """
    pass
