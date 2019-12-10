"""
Resource - Abstract subclass of django.db.models.Model.
 Base model class for shared objects management (no hierarchy between users),
 yet, users are not the ultimate proprietor of resources. They're contributors to a goal
 higher than themselves.

Explanatory:
=========
 Two modes exist: the shared, and the private.

 In the shared, users do not belong to orgs, nor the resources they create have any `owner`
 (meant for proprietorship) ; but a owner can create and manage resources (aka. Resource instances)
 across soft administrative boundaries (org, department, admin, etc.)

 In such shared mode, the created resources however have a viewing scope (hidden or not to users),
 that is the meaning assumed by default for the `namespaces` field available in every Resource instance.
 Hence, the resource's visibility can be modified dynamically.

Private operation, a single owner owns all resources (proprietorship).
 Although it is originally meant for the smartmodels app to function in shared mode, where the
 `namespaces` field on resources scopes their visibility, proprietorship of resources is emulated by setting
 at least the following in Django settings: `SMARTMODELS_NAMESPACE_MODEL = AUTH_USER_MODEL`.

Basic use cases:
=================
Use Resource in the place of django.db.models.Model for making smart functionality builtin in models,
 for providing features like:
 1) Administrative boundaries (eg. users create resources visible by more than one departments in an
    organization , or make contributions to several research domains, at once.
 2) Enabling the soft deletion (and instant recovery) of model instances,
    continue to show the contributions made by a deleted owner.
 3) Tracking the usage of resources by users, etc.

Features:
==========
More specifically, we:
    - Don't actually delete a model instance but just mark it so, then replace it by a sentinel owner.
    - Provide a SmartManager that filters out pseudo-deleted instances
    - Enforce (optional) the setting by api owner of `owner`, `created_by`, `updated_by` model attrs on saving.
    - Provide most builtin defaults to auto-configure the Django settings.
    - Provide a swappable `Namespace` model for further customization.

"""
from __future__ import absolute_import
from django.conf import settings
from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

from smartmodels.settings import get_setting, get_swappable_setting
from .perms import drop_perms
from .smart import SmartModel


def get_default_namespaces():
    """
    Whether owner or owner-domain (org, dept, etc.), return the default Namespace instance
     as a singleton list. It is created by default if SMARTMODELS_NAMESPACE_MODEL model DoesNotExists
    Also make the sentinel owner belong to the sentinel org.
    """
    namespace, created = get_namespace_model()._objects.get_or_create(**{
        get_setting('NAMESPACE_PK_FIELD'): get_setting('SENTINEL_UID'),
    })
    return list((namespace,))


def get_namespace_model():
    """
    Return the Owner model class (not string)
    that is active in this project.
    """

    model_string = get_setting('NAMESPACE_MODEL')
    try:
        return django_apps.get_model(model_string, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured("SMARTMODELS_NAMESPACE_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "SMARTMODELS_NAMESPACE_MODEL refers to model '%s' that has not been installed"
            % model_string
        )


class NameSpaceQuerySet(models.QuerySet):
    def on(self):
        return self.exclude(**{
            get_setting('NAMESPACE_PK_FIELD'): get_setting('SENTINEL_UID'),
        })


class NamespaceManager(models.Manager):
    def get_queryset(self):
        return NameSpaceQuerySet(self.model, using=self._db).on()


class AbstractNamespace(models.Model):
    """
    Top level domain (org, department, topic, etc.) which defines:
    1) the viewing scope of resources (Resource instances) created by users,
    2) the high level entity users are contributing to by creating resources.

    When picked up by Django settings (`SMARTMODELS_NAMESPACE_MODEL != AUTH_USER_MODEL),
     it means that the `distributed mode is active.
    """

    # TODO: Make the `name` field a configurable setting via custom metaclass
    name = models.SlugField(
        _("Namespace ID"),
        default='',
        max_length=get_setting('NAMESPACE_MAX_LENGTH'),
        help_text=_("Unique namespace ID. Configurable via the SMARTMODELS_OWNER_PK_FIELD setting."),
        unique=True, blank=False, null=False, editable=True,
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='%(class)ss',  # eg. user.namespaces, user.orgs, user.domains, etc.
        help_text=_("Contributors (users) to this org, department, etc.")
    )

    objects = NamespaceManager()
    _objects = models.Manager()

    class Meta:
        abstract = True

    def clean(self):
        self.name = slugify(self.name, allow_unicode=True)


class Namespace(AbstractNamespace):
    """
    Concrete, swappable implementation of Namespace.
    May represent some top level org, department, district, domain, (eg. admin), etc
    whom have shared "ownership" of resources (ShareResource's).
    """
    def __str__(self):
        return '%s' % self.name

    class Meta(AbstractNamespace.Meta):
        abstract = False
        swappable = get_swappable_setting()


class Resource(SmartModel):
    """
    Resource instances can be `owned` by several namespaces at once.
    If no valid namespace is set on creation, a resource inherit by default
     the namespaces of the owner that creates it.
    """
    # defaults to `shared_model.Namespace` instances. cf. smartmodels.settings
    namespaces = models.ManyToManyField(
        get_namespace_model(),
        related_name='%(class)ss_owned',
        help_text=_("Visibility domain: org, district, domain, etc.")
    )

    class Meta:
        abstract = True


@receiver(m2m_changed)
def prepare_shared_smart_fields(sender, instance, **kwargs):
    """
    Ensuring Resource subclasses will be saved with (*)all smart fields correctly set.
    Whether to require the smart fields' values from the api user (if `MODELS_DEFAULT_REQUIRED=True`)?
     Or to preset them with the defaults when the api user has not supplied them?

    (*) Only set the shared smart fields. Regular smart fields assumed already set by homologue
    method `prepare_smart_fields` for SmartModel subclasses.
    (*) We'nt aware whether it's a update or create op!
          Which fields need persisting to db is left up to high level api.
    """

    if issubclass(sender, Resource):

        # require the setting of all Resource fields by the api user
        # if requested so (`MODELS_DEFAULT_REQUIRED=True) otherwise,
        # use our own defaults presets.
        if get_setting('DEFAULT_REQUIRED'):
            assert instance.namespaces, (
                '{model_class}(SmartModel) instance missing "namespaces" attribute.'
                'To use the builtin defaults, set `SMARTMODELS_DEFAULT_REQUIRED=False`'
                'in  Django settings'
                .format(
                    model_class=instance.__class__.__name__
                )
            )
            assert instance.namespaces.exists(), (
                'The `namespaces` smart model field mustn\'t be empty since SMARTMODELS_DEFAULT_REQUIRED=True". '
                'Please supply  some {model_class} instances.'
                'To use the builtin defaults, set `SMARTMODELS_DEFAULT_REQUIRED=False`'
                'in  Django settings'
                .format(
                    model_class=type(instance.namespaces).__name__
                )
            )

    # forbid CRUDing namespace instances, superusers excepted.
    if issubclass(sender, Namespace):
        drop_perms(sender)


@receiver(m2m_changed)
def prepare_shared_smart_m2m_fields(sender, **kwargs):
    """
    Ensure the default (sentinel) namespace owns all of the resources all the time.
    """
    instance = kwargs['instance']
    action = kwargs['action']
    if isinstance(instance, Resource):
        if action == 'post_add' or action == 'post_remove' or action == 'post_clear':
            for space in get_default_namespaces():
                if space not in instance.namespaces.all():
                    # add the default namespace to this shared resource, without
                    # recursive `instance.namespaces.add(space)` call. would raise recursion error
                    getattr(space, '%ss_owned' % instance._meta.model_name).add(instance)


