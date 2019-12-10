# -*- coding: utf-8 -*-
import drf_loopback_js_filters
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response

from smartmodels.helpers import _make_smart_fields, _set_smart_fields

ALL_FIELDS = '__all__'


class SmartViewMixin(object):
    """
    Set/Get smart model fields based on the request.
    """

    def set_smart_fields(self, obj, action):
        """ Attach smart fields relevant to the view action, to obj """
        return _set_smart_fields(obj, action, self.request.user)

    def make_smart_fields(self, action):
        """ Dictionary of smart fields (and their respective values) relevant to the view action.
        Time-related field (created_at, updated_at, deleted_at) not trusted from the caller,
        and will be set by the instance base class SmartModel.
        """
        return _make_smart_fields(action, self.request.user)


class ResourceViewMixin(SmartViewMixin):
    """
    Set/get resource fields based on the request.
    """

    def make_smart_fields(self, action):
        smart_fields = super(ResourceViewMixin, self).make_smart_fields(action)
        smart_fields.update({
            'namespaces': self.get_namespaces(),
        })
        return smart_fields

    def get_namespaces(self):
        """
        Domains (Namespace's) the current resource (`self.get_object()`) belongs to.
        Creates or save a user's namespaces.
        On the resource's creation, the namespaces will default to the current user's namespaces,
         unless the request is asking set them to some specific (existing) values.
        If the logged in user has no namespace set, namespaces defaults to the builtins set by
         `get_default_namespace()` via the pre_save signal.

        """
        from smartmodels.models import get_namespace_model

        return [] if self.request.user.is_anonymous \
            else get_namespace_model().objects.filter(users__in=[self.request.user])


class OwnResourceViewMixin(ResourceViewMixin):
    """
    Restrict the objects worked upon to the set belonging to all the domains (namespaces)
    the currently logged in owner is subscribed to.

    In case of multiple inheritance, always place on the left-most side, to ensure
    object from the right scope as available.
     Eg.
     `
        class AccountEndpoint(OwnResourceViewMixin, SmartViewSet):
            pass
     `
    """

    def get_queryset(self):
        """
          Narrows down the set objects to work with (retrieve, list, etc.)
          to that belonging to the currently authenticated owner's own objects only.
          """
        qs = super(OwnResourceViewMixin, self).get_queryset()
        return qs.filter(owner=self.request.user)


class SmartSearchViewSetMixin(object):
    """
    Adds a `find` action/route to smart viewsets (ie., to `SmartViewSet` childs).
    Enables POST/GET requests to be sent like so:

    """
    sort_field_key = 'sort_field'
    sort_order_key = 'sort_order'
    page_number_key = 'page_number'
    page_size_key = 'page_size'

    def _build_search_params(self, data):
        return dict(
            filter=data.get('filter', None),
            sort=dict(
                order=data.get(self.sort_order_key, None),
                field=data.get(self.sort_field_key, None)
            ),
            page=dict(
                num=data.get(self.page_number_key, None),
                size=data.get(self.page_size_key, None)
            )
        )

    def _or_search(self, **kwargs):
        if kwargs:
            query = Q()
            for attr, value in kwargs.items():
                param = {'%s__icontains' % attr: value}
                query = query | Q(**param)
            return self.get_queryset().filter(query)
        return self.get_queryset().none()

    @action(detail=False, methods=['post', 'get'])
    def find(self, request):
        """
        Search
        :param request:
        :return: model items list
        """
        queryset = self.queryset
        search_params = self._build_search_params(
            self.request.data if self.request.method == 'POST' else self.request.query_params
        )

        if search_params['filter']:
            or_params = search_params['filter'].pop('or', None)
            if or_params:
                queryset = self._or_search(**or_params)
            queryset = queryset.filter(**search_params['filter'])

        if search_params['sort']:
            queryset = queryset.order_by("{order}{field}".format(
                field=search_params['sort']['field'],
                order='-' if search_params['sort']['order'] == 'desc' else '')
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SmartFilterViewSetMixin(object):
    filter_backends = [drf_loopback_js_filters.LoopbackJsFilterBackend]
