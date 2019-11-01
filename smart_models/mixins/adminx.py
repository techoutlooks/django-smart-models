from django.db.models import Q

from ..settings import SMART_FIELDS
from ..models import get_sentinel_user, get_default_namespace


class SmartModelAdminMixin(object):
    """
    Prevent the smart fields from showing up on admin views.
    Prevent the admin views from showing the sentinel user.
    """
    exclude = SMART_FIELDS


class SharedResourceAdminMixin(SmartModelAdminMixin):
    """
    Prevent the current user to see resources belonging to an org he is not subscribed to.
    Prevent the admin views from showing the default namespace (sentinel purposes).
    That does not apply to superusers.
    """
    def queryset(self):
        user = self.request.user
        qs = super(SharedResourceAdminMixin, self).queryset()
        mask = Q(owners__users__in=[user])

        if not user.is_superuser:
            qs = qs.filter(mask).distinct()
        return qs

    # def formfield_for_dbfield(self, db_field, **kwargs):
    #     from ..models import Namespace
    #     if db_field.name == 'namespaces':
    #         kwargs['queryset'] = Namespace.objects.exclude(*get_default_namespace()) #kwargs['queryset'].exclude(*get_default_namespace())
    #     return super(SharedResourceAdminMixin, self).formfield_for_dbfield(db_field, **kwargs)


