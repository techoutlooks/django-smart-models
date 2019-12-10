# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from smartmodels.drf.viewsets import ResourceViewSet
from .serializers import PostSerializer
from .models import Entity, Post, Question, Answer, Comment


class PostViewSet(ResourceViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
        # query_pk_and_slug = True
