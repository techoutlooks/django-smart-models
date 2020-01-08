# -*- coding: utf-8 -*-

from django.conf import settings
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from smartmodels.drf.views.bulk import BulkModelViewSet
from smartmodels.helpers import Action
from smartmodels.mixins import OwnResourceViewMixin, SmartViewMixin, ResourceViewMixin
from smartmodels.mixins.views import NamespaceResourceViewMixin
from smartmodels.settings import get_setting
from smartmodels.drf.serializers import NamespaceSerializer, OwnerSerializer, ResourceSerializer

from smartmodels.permissions import IsAdminOrIsOwner

from smartmodels.models import get_namespace_model, get_default_namespaces


class SmartViewSetMixin(SmartViewMixin):
    """
    Ensures that all smart fields are correctly set on the SmartView instances on CRUD ops.
     Eg. a resource's `namespaces`, creator, and update times are set automatically.

    Will raise an exception if `SMARTMODELS_DEFAULT_REQUIRED==True` and the smart
     fields were not supplied in the request by the API user (default behaviour).
    """
    permission_classes = [IsAdminOrIsOwner, ]

    # leverages save method's kwargs to save the instance's smart_fields,
    # as DRF just adds kwargs to validated_data under the scenes.

    def perform_create(self, serializer):
        serializer.save(**self.make_smart_fields(Action.CREATE))

    def perform_update(self, serializer):
        serializer.save(**self.make_smart_fields(Action.UPDATE))

    def perform_destroy(self, instance):
        self.set_smart_fields(instance, Action.DELETE)
        instance.delete(instance)


class SmartViewSet(SmartViewSetMixin, BulkModelViewSet):
    """
    Base class for all other smart class-based API views.
    Denies unauthenticated requests (important, as smartmodels by design tracks model instances owners.)
    """
    pass


class ReadOnlySmartViewSet(SmartViewSetMixin, ReadOnlyModelViewSet):
    """
    Smart model ViewSet that provides default `list()` and `retrieve()` actions.
    Denies unauthenticated requests (important, as smartmodels by design tracks model instances owners.)
    """
    pass


class ResourceViewSet(ResourceViewMixin, SmartViewSet):
    """
    SmartViewSet for CRUD ops on Resource instances.
    Admin or user-creator only allowed by default.
    Although if the objects proprietorship mode is emulated, assumes that the sentinel user is proprietary.
    """
    serializer_class = ResourceSerializer


class OwnResourceViewSet(OwnResourceViewMixin, ResourceViewSet):
    """
    SmartViewSet that displays the subset of resources from the current namespace's resources
    the currently logged in user is subscribed to.
    """
    pass


class NamespaceResourceViewSet(NamespaceResourceViewMixin, ResourceViewSet):
    """
    SmartViewSet that displays the subset of resources of the current namespace's resources
    the currently logged in user is subscribed to.
    """
    pass


class NamespaceViewSet(ModelViewSet):
    """
    Read-only. List all contribution domains (`namespaces`) a registering user is susceptible to subscribe to.
     This is the default workflow, as `SMARTMODELS_NAMESPACE_MODEL==Namespace` by design.
    If (planned exception) the User model emulates the contrib domain model, ie. users truly own objects,
     (`SMARTMODELS_NAMESPACE_MODEL==AUTH_USER_MODEL`), we assign ownership of all created objects to the designed
     list of default users (the builtin defaults to the sentinel user as a singleton queryset).

    To supply your own list of designed default namespaces, override static method `get_default_owners()` below.

    """
    serializer_class = NamespaceSerializer
    queryset = get_namespace_model().objects.all()

    def get_queryset(self):
        if get_setting('NAMESPACE_MODEL') == settings.AUTH_USER_MODEL:
            return get_default_namespaces()
        return super(NamespaceViewSet, self).get_queryset()
