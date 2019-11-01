"""
Smart Models

"""
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

__version__ = '0.1.0dev'


class SmartModelsAppConfig(AppConfig):
    name = 'smart_models'
    verbose_name = _('Smart Models')


default_app_config = 'smart_models.SmartModelsAppConfig'


