from django.db import models
from django.db.models import Q
from django.utils import timezone
from django_pandas.managers import DataFrameQuerySet, DataFrameManager

from smartmodels.settings import get_setting, get_owner_pk_field
from ..helpers import Action, _make_smart_fields
from .utils import get_sentinel_user


__all__ = [
    'SmartQuerySet',
    'SmartManagerMixin', 'SmartManager'
]


class SmartQuerySet(DataFrameQuerySet):

    def active(self):
        """
        Hide 1) the deleted instances 2) those whose creator (owner) has been deleted
        and  3) those belonging to the sentinel owner.
        """
        # FIXME: implement 2-3).
        # FIXME: get_sentinel_owner() exception trying to get instance 'coz models not loaded yet
        qs = self
        owner_pk_field = get_owner_pk_field()
        sentinel_filter = {"owner__{}".format(owner_pk_field): get_setting('SENTINEL_UID')}
        services_filter = {"owner__{}__in".format(owner_pk_field): get_setting('SERVICE_UIDS')}

        # hide what should be hidden
        qs = qs.exclude(Q(**sentinel_filter) | Q(owner__is_active=False,))
        if get_setting('HIDE_DELETED'):
            qs = qs.exclude(Q(deleted_at__isnull=False))
        if get_setting('HIDE_SERVICE_OWNERS'):
            qs = qs.exclude(Q(**services_filter) | Q(deleted_at__isnull=False))

        return qs

    def delete(self, deleted_by=None, **kwargs):
        """
        Fake-delete an entire queryset.
        Hooked when call looks like: SmartX.objects.filter(**opts).delete()
        :return: Nothing
        """
        if get_setting('DEFAULT_REQUIRED'):
            assert deleted_by, (
                '{model_class}(SmartModel) manager method `delete()` missing "deleted_by" attribute.'
                'To use the builtin defaults, set `SMARTMODELS_DEFAULT_REQUIRED=False`'
                'in  Django settings'.format(
                    model_class=self.__class__.__name__
                )
            )
        return super(SmartQuerySet, self)\
            .update(deleted_at=timezone.now(), deleted_by=deleted_by, owner=get_sentinel_user(), **kwargs)

    def _delete(self):
        """
        Original QuerySet.delete() method above.
        """
        return super(SmartQuerySet, self).delete()

    def create(self, owner, **kwargs):
        smfields = _make_smart_fields(action=Action.CREATE, owner=owner)
        kwargs.update(smfields)
        return super().create(**kwargs)


class SmartManagerMixin(object):
    """
    Building block for defining objects managers suitable for SmartModel-based objects.
    """
    # TODO: verify() for all obj creation methods: update_or_create(), create(), etc.
    queryset_cls = None

    def get_queryset(self):
        return self.queryset_cls(self.model, using=self._db).active()


class SmartManager(SmartManagerMixin, DataFrameManager):
    """
    Needed for manager function chaining.
    """
    queryset_cls = SmartQuerySet


