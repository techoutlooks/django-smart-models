from rest_framework.generics import get_object_or_404


class PrivateResourceViewMixin(object):
    """
    Provides overrides for displaying the currently logged in user's private resources only.
    In case of multiple inheritance, always place on the left-most side, to ensure
    that a user's private resources are never disclosed to others.

     Eg.
     `
        class AccountEndpoint(PrivateResourceViewMixin, SmartModelViewSet):
            pass
     `
    """
    def get_object(self):
        """
        The object this view is displaying has to be
         the currently authenticated user's own.
         Permissions are also checked (by super method)
        """

        plain_obj = super(PrivateResourceViewMixin, self).get_object()
        obj = get_object_or_404(self.get_queryset(), **{
            self.get_smart_model().user: self.request.user
        })
        return obj

    def get_queryset(self):
        """
        Narrows down the set objects to work with (retrieve, list, etc.)
        to that belonging to the currently authenticated user's own objects only.
        """
        return super(PrivateResourceViewMixin, self).get_queryset().filter(**{
            self.get_smart_model().user: self.request.user
        })


class SubscribedResourceViewMixin(object):
    """
    Restrict the objects worked upon to the set belonging to all the domains (Shareholers)
    the currently logged in user is subscribed to.

    In case of multiple inheritance, always place on the left-most side, to ensure
    object from the right scope as available.
     Eg.
     `
        class AccountEndpoint(SubscribedResourceViewMixin, SmartModelViewSet):
            pass
     `
    """
    pass
