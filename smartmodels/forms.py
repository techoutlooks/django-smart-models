# from django.forms import ModelForm
#
# from smartmodels.views.mixins import SmartViewMixin, ResourceViewMixin
# from smartmodels.helpers import Action
#
#
# class SmartForm(SmartViewMixin, ModelForm):
#
#     def save(self, commit=True):
#         action = Action.UPDATE if self.instance.pk else Action.CREATE
#         self.set_smart_fields(self.instance, action)
#         return super().save(commit)
#
#
# class ResourceForm(ResourceViewMixin, SmartForm):
#     pass

