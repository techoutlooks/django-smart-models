from __future__ import absolute_import

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.decorators import classproperty
from django.utils.translation import gettext_lazy as _

from ..settings import get_setting


def get_sentinel_user():
    """
    Sentinel instance, of the AUTH_USER_MODEL model.
    """
    user, created = get_user_model().objects.get_or_create(username=get_setting('SENTINEL_UID'))
    return user


class SmartQuerySet(models.QuerySet):

    def active(self):
        """
        Hide 1) the deleted instances 2) those whose creator (user) has been deleted
        and  3) those belonging to the sentinel user.
        """
        # FIXME: implement 2-3).
        # FIXME: get_sentinel_owner() exception trying to get instance 'coz models not loaded yet
        qs = self
        sentinel_filter = {"user__{}".format(get_user_model().USERNAME_FIELD): get_setting('SENTINEL_UID')}

        qs.exclude(
            Q(**sentinel_filter),
            user__is_active=False,
        )

        if get_setting('RESOURCES_SHOW_DELETED'):
            return qs
        return qs.filter(deleted_at=None)

    def delete(self, deleted_by=None):
        """
        Fake-delete an entire queryset.
        Hooked when call looks like: SmartX.objects.filter(**opts).delete()
        """
        return super(SmartQuerySet, self).update(deleted_at=timezone.now(), deleted_by=deleted_by)

    def _delete(self):
        """
        Original QuerySet.delete() method above.
        """
        return super(SmartQuerySet, self).delete()


class SmartManager(models.Manager):
    """

    """

    # TODO: verify() for all obj creation methods: update_or_create(), create(), etc.

    def get_queryset(self):
        return SmartQuerySet(self.model, using=self._db).active()


class AbstractSmartModel(models.Model):
    """
    Abstract Model for enabling the tracking of various per-Account actions
     at the model level, including the deletion (soft by default) of objects.

    """
    # FIXME: set default owner on creation
    # TODO: API for restoring deleted instances !

    deleted_at = models.DateTimeField(_('deleted at'), blank=True, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('modified at'), auto_now=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        on_delete=models.SET(get_sentinel_user),
        related_name='%(class)ss',
        help_text=_('User obo. whom this resource is created. The sentinel user on deletion.')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        on_delete=models.SET(get_sentinel_user),
        related_name='%(class)ss_created',
        help_text=_('Creator (user) of the resource.')
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        on_delete=models.SET(get_sentinel_user),
        related_name='%(class)ss_updated'
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        on_delete=models.SET(get_sentinel_user),
        related_name='%(class)ss_deleted'
    )

    # default_manager is SmartManager
    # but also keep copy of original manager as _objects
    objects = SmartManager()
    _objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, deleted_by=None, using=None, keep_parents=False):
        """
        Model.delete() override that also mark model as deleted and by whom.

        Owner of the model is changed to the sentinel user by the ORM behind the scene
        through `on_delete=models.SET(get_sentinel_user)`. Cf the user field definition.
        """
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.user = get_sentinel_user()

        # route to prepare_smart_fields()
        self.save()


@receiver(pre_save)
def prepare_smart_fields(sender, instance, **kwargs):
    """
    Ensures AbstractSmartModel subclasses will be saved with (*)all smart fields correctly set.
    Will require the smart fields' values set from higher lever API if `MODELS_DEFAULT_REQUIRED=True`
    Set `MODELS_DEFAULT_REQUIRED=False` to emulate regular models (ignore the smart fields).

    (*) We are'nt aware whether it's a update or create op, nor what user achieves it!
    (*) Values for `created_by`, `updated_by` `deleted_by` must be set by the higher level api.
    """
    # TODO: delete not handled yet !
    if issubclass(sender, AbstractSmartModel):

        # require the setting of all SharedResource fields by the api user
        # if requested so (`MODELS_DEFAULT_REQUIRED=True) otherwise,
        # use our own defaults presets.
        if get_setting('DEFAULT_REQUIRED'):
            assert instance.created_by, (
                '{model_class}(AbstractSmartModel) instance missing "created_by" attribute.'
                'To use the builtin defaults, set `SMART_MODELS_DEFAULT_REQUIRED=False`'
                'in  Django settings'.format(
                    model_class=instance.__class__.__name__
                )
            )
            assert instance.updated_by, (
                '{model_class}(AbstractSmartModel) instance missing "updated_by" attribute.'
                'To use the builtin defaults, set `SMART_MODELS_DEFAULT_REQUIRED=False`'
                'in  Django settings'.format(
                    model_class=instance.__class__.__name__
                )
            )
            assert instance.user, (
                '{model_class}(AbstractSmartModel) instance missing "user" attribute.'
                'To use the builtin defaults, set `SMART_MODELS_DEFAULT_REQUIRED=False`'
                'in  Django settings'.format(
                    model_class=instance.__class__.__name__
                )
            )

        # use the builtin defaults,
        # because MODELS_DEFAULT_REQUIRED=True
        else:
            time = timezone.now()
            sentinel_user = get_sentinel_user()
            # user = instance.user or sentinel_user
            smart_fields = dict(
                # user=user,
                updated_at=time
            )
            if instance.pk:
                smart_fields.update(created_at=time)

            for attr, value in smart_fields.items():
                setattr(instance, attr, value)
