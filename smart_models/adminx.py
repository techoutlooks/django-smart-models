from xadmin import site

from .models import Namespace


class NamespaceAdmin(object):

    def get_model_perms(self):
        """ Deny all permissions to perform any action on Namespace instances.
        This only removes corresponding action buttons. Effective permission removal being done at model-level.
         Is additional care, since perms dropping has hidden the model already."""
        if not self.request.user.is_superuser:
            return dict(view=False, add=False, change=False, delete=False)
        return super(NamespaceAdmin, self).get_model_perms()


site.register(Namespace, NamespaceAdmin)
