from __future__ import absolute_import
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from msg7.auth7.models import Permission

logger = logging.getLogger(__name__)


def permission_names_to_objects(names):
    """
    Given an iterable of permission names (e.g. 'app_label.add_model'),
    return an iterable of Permission objects for them.  The permission
    must already exist, because a permission name is not enough information
    to create a new permission.
    """
    result = []
    for name in names:
        app_label, codename = name.split(".", 1)
        # Is that enough to be unique? Hope so
        try:
            result.append(Permission.objects.get(content_type__app_label=app_label,
                                                 codename=codename))
        except Permission.DoesNotExist:
            logger.exception("NO SUCH PERMISSION: %s, %s" % (app_label, codename))
            raise
    return result


def remove_perms(perms):
    # drop perms for any group
    for group in Group.objects.all():
        group.permissions.remove(*perms)

    # drop perms also for individual users,
    # in case certain users are not subcribed to any group
    for user in get_user_model().objects.all():
        user.user_permissions.remove(*perms)
    return perms
