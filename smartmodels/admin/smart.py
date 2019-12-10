from django.contrib import admin
from smartmodels.models import Namespace


class NamespaceAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """ Deny all permissions to perform any action on Namespace instances.
        This only removes corresponding action buttons. Effective permission removal being done at model-level.
         Is additional care, since perms dropping has hidden the model already."""
        if not request.user.is_superuser:
            return dict(view=False, add=False, change=False, delete=False)
        return super(NamespaceAdmin, self).get_model_perms(request)


admin.site.register(Namespace, NamespaceAdmin)
