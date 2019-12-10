from enum import Enum

from django.contrib.auth import get_user_model

from smartmodels.settings import get_owner_pk_field, get_setting, USER_SMART_FIELDS


class Action(Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'


def _has_smart_fields(instance):
    """
    Whether the smart fields are correctly set.
    """
    return all(getattr(instance, field) for field in USER_SMART_FIELDS)


def _make_smart_fields(action, owner):
    """
    Dictionary of smart fields (and their respective values) relevant to the view action.
    Time-related field (created_at, updated_at, deleted_at) not trusted from the caller,
    and will be set under the scene by the instance base class SmartModel.
    """
    fields = {}

    if action == Action.CREATE:
        fields.update(owner=owner, created_by=owner, updated_by=owner)
    elif action == Action.UPDATE:
        fields.update(updated_by=owner)
    elif action == Action.DELETE:
        fields.update(deleted_by=owner)

    return fields


def _set_smart_fields(obj, action, user):
    """
    Attach smart fields relevant to the view action, to obj.
    """
    for attr, value in _make_smart_fields(action, user).items():
        setattr(obj, attr, value)
    return obj


def _are_services(instance, uid=None, uids=[]):
    """
    Whether instance is the sentinel for the user or namespace model.
    :param instance: instance of User or Namespace.
    :return: bool
    """
    if uid:
        uids.append(uid)

    if isinstance(instance, get_user_model()):
        _USERNAMEFIELD = get_owner_pk_field()
        return getattr(instance, _USERNAMEFIELD) in uids
    return False


def is_sentinel(instance):
    """
    Whether instance is the sentinel for the user or namespace model.
    :param instance: instance of User or Namespace.
    :return: bool
    """
    return _are_services(instance, uid=get_setting('SENTINEL_UID'))


def is_service(instance):
    return _are_services(instance, uids=get_setting('SERVICE_UIDS'))


def is_superuser(instance):
    """
    Whether instance is a superuser.
    Superuser mightn't have any owner (smartfield `owner=None`).
    :param instance: any objet
    :return: bool
    """
    if isinstance(instance, get_user_model()):
        return instance.is_superuser
    return False


def get_owner(instance):
    """
    Which user owns `instance`?
    :param instance: SmartModel instance expected.
    :return: instance of current user model.
    """
    from smartmodels.models import SmartModel

    # disregard this value for non-smartmodel instances.
    if not issubclass(instance.__class__, SmartModel):
        return None

    # nobody owns the sentinel but the sentinel
    if is_sentinel(instance):
        return instance
    return instance.owner


class SmartModelFactoryMixin(object):

    def set_smart_fields(self, action, owner):
        return _set_smart_fields(self, action, owner)

    def make_smart_fields(self, action, owner):
        return _make_smart_fields(action, owner)

    def has_smart_fields(self):
        return _has_smart_fields(self)
