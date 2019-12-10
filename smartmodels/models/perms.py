from __future__ import absolute_import
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from django.contrib.auth.models import Permission

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


def assign_perm(perm, group):
    """
    Assigns a permission to a group
    """
    if not isinstance(perm, Permission):
        try:
            app_label, codename = perm.split('.', 1)
        except ValueError:
            raise ValueError("For global permissions, first argument must be in"
                             " format: 'app_label.codename' (is %r)" % perm)
        perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)

    group.permissions.add(perm)
    return perm


def remove_perm(perm, group):
    """
    Removes a permission from a group
    """
    if not isinstance(perm, Permission):
        try:
            app_label, codename = perm.split('.', 1)
        except ValueError:
            raise ValueError("For global permissions, first argument must be in"
                             " format: 'app_label.codename' (is %r)" % perm)
        perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)

    group.permissions.remove(perm)
    return


def drop_perms(model):
    """
    Prevent users and groups from tampering with the namespace model (settings.SMARTMODELS_NAMESPACE_MODEL).
    Also applies owner-defined permissions. Has no effect on superusers.
    :param: model: model class (or instance) of owner model.
    :return: perms_denied: the successfully removed permissions
    """
    default = set(('add', 'change', 'delete', 'view')) | set(model._meta.default_permissions)
    codenames = ['%s_%s' % (action, model._meta.model_name) for action in default]
    perms_denied = permission_names_to_objects(['%s.%s' % (app_label, code) for code in codenames])
    return remove_perms(perms_denied)
