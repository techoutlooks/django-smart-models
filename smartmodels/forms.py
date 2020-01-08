from django.forms import ModelForm

from smartmodels.helpers import Action, _set_smart_fields
from smartmodels.mixins import SmartViewMixin, ResourceViewMixin
from smartmodels.models import get_namespace_model
from oneauth.middleware import get_current_user, get_current_authenticated_user


Namespace = get_namespace_model()


class SmartForm(ModelForm):
    """
    Base model form for smartmodel instances.
    """

    _current_user = None

    def save(self, commit=True):
        action = Action.UPDATE if self.instance.pk else Action.CREATE
        _set_smart_fields(self.instance, action, self.current_user)
        return super().save(commit)

    @property
    def current_user(self):
        if self._current_user:
            return self._current_user
        self._current_user = get_current_authenticated_user()
        return self._current_user


class ResourceForm(ResourceViewMixin, SmartForm):
    """
    For use with tenant-enabled objects (resources).
    Prevent the currently logged in user to see the namespaces she/he is not subscribed to.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_orgs = self.fields['orgs']

        if not self.current_user:
            user_orgs.queryset = Namespace.objects.none()
        user_orgs.queryset = self.current_user.orgs.all()
