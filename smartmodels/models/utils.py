from django.contrib.auth import get_user_model

from smartmodels.settings import get_setting, get_owner_pk_field


def get_sentinel_user():
    """
    Sentinel instance, of the AUTH_USER_MODEL model.
    """

    # sentinel is hidden from the regular `objects` namager,
    # use the default manager
    user, created = get_user_model()._objects.get_or_create(
        **{get_owner_pk_field(): get_setting('SENTINEL_UID')}
    )
    return user
