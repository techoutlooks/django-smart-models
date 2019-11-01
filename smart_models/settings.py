"""
Django settings for the SharedResource's.
"""

app_label = 'smart_models'
SMART_FIELDS = ['user', 'created_by', 'updated_by', 'deleted_by', 'created_at', 'updated_at', 'deleted_at']
add_prefix = lambda x: '%s_%s' % (app_label.upper(), x.upper())


DEFAULT_MODELS_OWNER_PK_FIELD = 'name'
DEFAULT_MODELS_OWNER = {
    'model': '%s.Namespace' % app_label,
    'pk_field': DEFAULT_MODELS_OWNER_PK_FIELD,
    'uid': 'sentinel',
}


def get_setting(name):
    """
    Get configured Django setting or the app's builtin.
    :param name: setting name without the `SMART_` prefix.
    :return: value for setting.
    """
    # TODO: SMART_MODELS_RESOURCES_SHOW_DELETED:
    # whether to continue showing up resource whose creator (user) has been (soft) deleted.
    # set option for enabling in the manager [and (necessary?) in the base view (the returned objects)].
    # TODO: systematically add queried settings to Django settings (by calling add_setting).

    from django.conf import settings
    from django.contrib.auth import get_user_model

    def get_owner_pk_field():
        """
        A string. The User model's USERNAME_FIELD if the Namespace model is the User model,
        the `name` field otherwise.
        """
        if getattr(settings, 'SMART_MODELS_OWNER_MODEL', None) == settings.AUTH_USER_MODEL:
            return get_user_model().USERNAME_FIELD
        return DEFAULT_MODELS_OWNER['pk_field']

    return {
        add_prefix('RESOURCES_SHOW_DELETED'): getattr(settings, add_prefix('RESOURCES_SHOW_DELETED'), False),
        add_prefix('SENTINEL_UID'): getattr(settings, add_prefix('SENTINEL_UID'), DEFAULT_MODELS_OWNER['uid']),
        add_prefix('OWNER_PK_FIELD'): getattr(settings, add_prefix('OWNER_PK_FIELD'), get_owner_pk_field()),
        add_prefix('OWNER_MODEL'): getattr(settings, add_prefix('OWNER_MODEL'), DEFAULT_MODELS_OWNER['model']),
        add_prefix('DEFAULT_REQUIRED'): getattr(settings, add_prefix('DEFAULT_REQUIRED'), True),
        add_prefix('OWNER_PK_FIELD'): getattr(settings, add_prefix('OWNER_PK_FIELD'), DEFAULT_MODELS_OWNER_PK_FIELD)

    }.get('%s_%s' % (app_label.upper(), name))


def add_setting(name, value):
    """
    Add name/value pair to settings module.
     Expects setting name with prefix `SMART_` stripped
     eg. MODELS_OWNER_MODEL to produce SMART_MODELS_OWNER_MODEL=<value>
     FIXME: Not patching settings at runtime when using django-configurations as it should do! not harmful?
    """
    from django.conf import settings

    setting = '%s_%s' % (app_label.upper(), name)

    # Ensure this attribute exists to avoid migration issues in Django 1.7
    if not hasattr(settings, setting):
        setattr(settings, setting, value)
    return setting


def get_swappable_setting():
    """
    Returns the setting name to use for the given model (i.e. SMART_MODELS_OWNER_MODEL)
    after having set its value to Django settings.
    """
    return add_setting(name='OWNER_MODEL', value=get_setting('OWNER_MODEL'))
