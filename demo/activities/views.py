# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from smartmodels.drf.viewsets import ResourceViewSet
from .serializers import ActivitySerializer


class ActivityViewSet(ResourceViewSet):
    serializer_class = ActivitySerializer
