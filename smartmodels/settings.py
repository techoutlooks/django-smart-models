"""
Default Django settings `smartmodels`.
"""

app_label = 'smartmodels'


# USER_SMART_FIELDS: Must set by views (user from request) on SmartModel instances
# TIME_SMART_FIELDS: set automatically on SmartModel instances
USER_SMART_FIELDS = ['owner', 'created_by', 'updated_by', 'deleted_by']
TIME_SMART_FIELDS = ['created_at', 'updated_at', 'deleted_at']
RESOURCE_SMART_FIELDS = ['namespaces']
SMART_FIELDS = TIME_SMART_FIELDS + USER_SMART_FIELDS + RESOURCE_SMART_FIELDS

# Default namespace's settings.
DEFAULT_NAMESPACE_MAX_LENGTH = 100
DEFAULT_NAMESPACE_PK_FIELD = 'slug'

# Who owns any model by default?
DEFAULT_MODELS_OWNER_UID = 'sentinel'

# UIDs of services that own resources.
# Checking of smart fields for related owners are disabled.
DEFAULT_SERVICE_UIDS = []

add_prefix = lambda x: '%s_%s' % (app_label.upper(), x.upper())


def get_owner_pk_field():
    """
    A string. The current user model's USERNAME_FIELD.
    """
    from django.contrib.auth import get_user_model
    return get_user_model().USERNAME_FIELD


def get_setting(name):
    """
    Get configured Django setting or the app's builtin.
    :param name: setting name without the `SMART_` prefix.
    :return: value for setting.
    """
    # TODO: SMARTMODELS_HIDE_DELETED:
    # whether to continue showing up resource whose creator (owner) has been (soft) deleted.
    # set option for enabling in the manager [and (necessary?) in the base view (the returned objects)].
    # TODO: systematically add queried settings to Django settings (by calling add_setting).

    from django.conf import settings

    return {
        'SENTINEL_UID': getattr(settings, add_prefix('SENTINEL_UID'), DEFAULT_MODELS_OWNER_UID),
        'SERVICE_UIDS': getattr(settings, add_prefix('SERVICE_UIDS'), DEFAULT_SERVICE_UIDS),
        'NAMESPACE_PK_FIELD': getattr(settings, add_prefix('NAMESPACE_PK_FIELD'), DEFAULT_NAMESPACE_PK_FIELD),
        'NAMESPACE_MODEL': getattr(settings, add_prefix('NAMESPACE_MODEL'), '%s.namespace' % app_label),
        'NAMESPACE_MAX_LENGTH': getattr(settings, add_prefix('NAMESPACE_MAX_LENGTH'), DEFAULT_NAMESPACE_MAX_LENGTH),

        # Yes/No options
        'DEFAULT_REQUIRED': getattr(settings, add_prefix('DEFAULT_REQUIRED'), True),
        'HIDE_SERVICE_OWNERS': getattr(settings, add_prefix('HIDE_SERVICE_OWNERS'), False),
        'HIDE_DELETED': getattr(settings, add_prefix('HIDE_DELETED'), True),

    }.get(name)


def add_setting(name, value):
    """
    Add name/value pair to settings module.
     Expects setting name with prefix `SMART_` stripped
     eg. MODELS_NAMESPACE_MODEL to produce SMARTMODELS_NAMESPACE_MODEL=<value>
     FIXME: Not patching settings at runtime when using django-configurations as it should do! not harmful?
    """
    from django.conf import settings

    # TODO: add_prefix() ??
    setting = '%s_%s' % (app_label.upper(), name)

    # Ensure this attribute exists to avoid migration issues in Django 1.7
    if not hasattr(settings, setting):
        setattr(settings, setting, value)
    return setting


def get_swappable_setting():
    """
    Returns the setting name to use for the given model (i.e. SMARTMODELS_NAMESPACE_MODEL)
    after having set its value to Django settings.
    """
    return add_setting(name='NAMESPACE_MODEL', value=get_setting('NAMESPACE_MODEL'))
