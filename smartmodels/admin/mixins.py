# -*- coding: utf-8 -*-
import threading
from django.db.models import Q

from smartmodels.helpers import Action
from smartmodels.settings import SMART_FIELDS
from smartmodels.mixins import SmartViewMixin


class ModelAdminRequestMixin(object):
    """
    Mixin for saving/accessing the request as self.request in Django ModelAdmin.
    Credits: http://marcelchastain.com/2018/05/getting-access-to-request-in-django-modeladmin/
    """
    def __init__(self, *args, **kwargs):
        # let's define this so there's no chance of AttributeErrors
        self._request_local = threading.local()
        self._request_local.request = None
        super(ModelAdminRequestMixin, self).__init__(*args, **kwargs)

    def get_request(self):
        return self._request_local.request

    def set_request(self, request):
        self._request_local.request = request

    request = property(get_request, set_request)

    def changeform_view(self, request, *args, **kwargs):
        # stash the request
        self.set_request(request)

        # call the parent view method with all the original args
        return super(ModelAdminRequestMixin, self).changeform_view(request, *args, **kwargs)

    def add_view(self, request, *args, **kwargs):
        self.set_request(request)
        return super(ModelAdminRequestMixin, self).add_view(request, *args, **kwargs)

    def change_view(self, request, *args, **kwargs):
        self.set_request(request)
        return super(ModelAdminRequestMixin, self).change_view(request, *args, **kwargs)

    def changelist_view(self, request, *args, **kwargs):
        self.set_request(request)
        return super(ModelAdminRequestMixin, self).changelist_view(request, *args, **kwargs)

    def delete_view(self, request, *args, **kwargs):
        self.set_request(request)
        return super(ModelAdminRequestMixin, self).delete_view(request, *args, **kwargs)

    def history_view(self, request, *args, **kwargs):
        self.set_request(request)
        return super(ModelAdminRequestMixin, self).history_view(request, *args, **kwargs)


class SmartModelAdminMixin(SmartViewMixin, ModelAdminRequestMixin):
    """
    Prevent the smart fields from showing up on admin views.
    Prevent the admin views from disclosing the sentinel owner.
    """
    exclude = SMART_FIELDS
    # actions = ['delete_selected',]

    def save_model(self, request, obj, form, change):
        action = Action.UPDATE if change else Action.CREATE
        self.set_smart_fields(obj, action)

        super(SmartModelAdminMixin, self).save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """ When called from instance change form. """
        self.set_smart_fields(obj, Action.DELETE)
        super(SmartModelAdminMixin, self).delete_model(request, obj)

    # Compat with Django<2.1
    def delete_selected(self, request, queryset):
        return self._delete(queryset, request.user)

    # Django>=2.1 only.
    # https://docs.djangoproject.com/en/2.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.delete_queryset
    def delete_queryset(self, request, queryset):
        return self._delete(queryset, request.user)

    def _delete(self, queryset, deleted_by):
        # noqa, but avoids calling `queryset.delete(deleted_by=request.user)`, instead
        # `instance.delete()` triggers `post_delete` signal to give listeners a chance;
        # eg. Account model defining a OneToOneField(User) requires `post_delete`
        # to initiate user account deletion as the corresponding user gets deleted (cf. demo).
        for obj in queryset:
            self.set_smart_fields(obj, Action.DELETE)
            obj.delete()


class ResourceAdminMixin(SmartModelAdminMixin):
    """
    Prevent the current owner to see resources belonging to an org he is not subscribed to.
    Prevent the admin views from showing the default namespace (sentinel purposes).
    That does not apply to superusers.
    """

    def get_queryset(self, request):
        qs = super(ResourceAdminMixin, self).get_queryset(request)
        user_resources = Q(namespaces__users__in=[request.user])

        if not request.user.is_superuser:
            qs = qs.filter(user_resources).distinct()
        return qs

    # def formfield_for_dbfield(self, db_field, **kwargs):
    #     from ..models import Namespace
    #     if db_field.name == 'namespaces':
    #         kwargs['queryset'] = Namespace.objects.exclude(*get_default_namespace()) #kwargs['queryset'].exclude(*get_default_namespace())
    #     return super(ResourceAdminMixin, self).formfield_for_dbfield(db_field, **kwargs)

