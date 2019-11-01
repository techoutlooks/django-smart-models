from __future__ import absolute_import

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from ..models import AbstractSmartModel, get_sentinel_user
from ..settings import get_setting


class PrivateResource(AbstractSmartModel):
    """
    A user's owned resource.
    Eg. My account, my contacts, my preferences.

    Such resource still benefits the SmartModel machinery, eg. tracking of model-level events, etc.
    Requires Django settings to have SMART_MODELS_OWNER_MODEL different from the shared owner model,
     which defaults to 'shared_model.Namespace'. Set for eg. SMART_MODELS_OWNER_MODEL='auth.User' in
     your Django settings to enable the Private (proprietorship) mode.
    """

    class Meta:
        abstract = True

    # FIXME: DELETEME: has been superseded by the 'user' field on AbstractSmartModel
    # @property
    # def owner_lookup_field(self):
    #     """
    #     Model field lookup attribute from this model, pointing the user the model instance belongs to.
    #     Eg. usage:
    #
    #     class Contact(PrivateResource):
    #         def get_user_field_lookup(self):
    #             return 'contact__account__user'
    #
    #     We want to be able to call it from higher level api like so:
    #     `
    #         def get_object(self):
    #             return get_object_or_404(self.get_queryset(), **{
    #                 self.request.user.get_user_field_lookup(): self.request.user
    #     `
    #     })
    #
    #     """
    #     raise NotImplementedError('`get_user_field_lookup()` must be implemented.')
