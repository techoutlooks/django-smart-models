# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.decorators import classproperty
from django.utils.translation import gettext_lazy as _

from smartmodels.helpers import is_sentinel, is_superuser, is_service, SmartModelFactoryMixin
from smartmodels.settings import get_setting, get_owner_pk_field

from .utils import get_sentinel_user
from .managers import SmartManager


__all__ = ['SmartModel']


class SmartModel(SmartModelFactoryMixin, models.Model):
    """
    Abstract Model for enabling the tracking of various per-Account actions
     at the model level, including the deletion (soft by default) of objects.

    """
    # FIXME: set default owner on creation
    # TODO: API for restoring deleted instances !

    deleted_at = models.DateTimeField(_('deleted at'), blank=True, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('modified at'), auto_now=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        on_delete=models.SET(get_sentinel_user),
        related_name='%(class)ss_owned',
        help_text=_('User obo. whom this resource is created. The sentinel owner on deletion.')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        on_delete=models.SET(get_sentinel_user),
        related_name='%(class)ss_created',
        help_text=_('Creator (owner) of the resource.')
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

    def delete(self, using=None, keep_parents=False):
        """
        Model.delete() override that also mark model as deleted and by whom.
        Requires the `deleted_by` field to be set by the caller, if SMARTMODELS_DEFAULT_REQUIRED=True.

        Owner of the model is changed to the sentinel owner by the ORM behind the scene
        through `on_delete=models.SET(get_sentinel_user)`. Cf the owner field definition.
        """

        # this is a guard to ensure `deleted_by` is set
        # so that we know we deletes an instance
        if get_setting('DEFAULT_REQUIRED'):
            assert self.deleted_by, (
                '{model_class}(SmartModel) instance missing "deleted_by" attribute.'
                'To use the builtin defaults, set `SMARTMODELS_DEFAULT_REQUIRED=False`'
                'in  Django settings'.format(
                    model_class=self.__class__.__name__
                )
            )

        self.deleted_at = timezone.now()
        self.owner = get_sentinel_user()

        # calling save instead of regular `delete()` method,
        # will route to the `smartmodels.models.prepare_smart_fields()` pre_save signal handler
        # also, let's manually fire the `post_delete` signal to leave change to listeners to cope with the deletion.
        post_delete.send(sender=self.__class__, instance=self, deleted_by=self.deleted_by)
        self.save()


@receiver(pre_save)
def prepare_smart_fields(sender, instance, **kwargs):
    """
    Ensures SmartModel subclasses will be saved with (*)all smart fields correctly set.
    Will require the smart fields' values set from higher lever API if `MODELS_DEFAULT_REQUIRED=True`
    Set `MODELS_DEFAULT_REQUIRED=False` to emulate regular models (ignore the smart fields).

    (*) We are'nt aware whether it's a update or create op, nor what owner achieves it!
    (*) Values for `created_by`, `updated_by` `deleted_by` must be set by the higher level api.
    """
    # TODO: delete not handled yet !
    if issubclass(sender, SmartModel):

        # require the setting of all Resource fields by the api owner
        # if requested so (`MODELS_DEFAULT_REQUIRED=True) otherwise,
        # use our own defaults presets.
        excluded = is_sentinel(instance) or is_superuser(instance) or is_service(instance)
        if get_setting('DEFAULT_REQUIRED') and not excluded:
            assert instance.owner, (
                '{model_class}(SmartModel) instance missing "owner" attribute. '
                'To use the builtin defaults, set `SMARTMODELS_DEFAULT_REQUIRED=False`'
                'in  Django settings'.format(
                    model_class=instance.__class__.__name__
                )
            )
            if not instance.pk:
                assert instance.created_by and instance.updated_by, (
                    '{model_class}(SmartModel) instance missing "created_by" or "updated_by" attribute. '
                    'To use the builtin defaults, set `SMARTMODELS_DEFAULT_REQUIRED=False`'
                    'in  Django settings'.format(
                        model_class=instance.__class__.__name__
                    )
                )
            else:
                assert instance.updated_by or instance.deleted_by, (
                    '{model_class}(SmartModel) instance missing "updated_by" or "deleted_by" attribute. '
                    'To use the builtin defaults, set `SMARTMODELS_DEFAULT_REQUIRED=False`'
                    'in  Django settings'.format(
                        model_class=instance.__class__.__name__
                    )
                )

        # use the builtin defaults,
        # because MODELS_DEFAULT_REQUIRED=True
        else:
            time = timezone.now()
            smart_fields = dict(
                updated_at=time
            )
            if not instance.pk:
                smart_fields.update(created_at=time)

            for attr, value in smart_fields.items():
                setattr(instance, attr, value)
