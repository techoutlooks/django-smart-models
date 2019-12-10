from __future__ import absolute_import

from .smart import SmartModel
from .managers import SmartManager, SmartQuerySet
from .utils import get_sentinel_user

from .resource import (
    AbstractNamespace, Resource, Namespace,
    get_namespace_model, get_default_namespaces,
)
