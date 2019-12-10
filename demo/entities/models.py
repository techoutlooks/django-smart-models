# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.urls import reverse
from django.utils.text import slugify

from smartmodels.models import Resource

from activities.models import Activity


BLOG_TITLE_MAX_LENGTH = 100


class Entity(Resource):
    title = models.CharField(
        max_length=BLOG_TITLE_MAX_LENGTH
    )
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=BLOG_TITLE_MAX_LENGTH,
    )

    class Meta:
        abstract = True

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('entity-pk-slug-detail', kwargs=kwargs)

    def save(self, *args, **kwargs):
        value = self.title
        self.slug = slugify(value, allow_unicode=True)
        super(Entity, self).save(*args, **kwargs)


class Post(Entity):
    likes = GenericRelation(Activity)

    def __str__(self):
        return self.title


class Question(Entity):
    activities = GenericRelation(Activity)


class Answer(Entity):
    votes = GenericRelation(Activity)


class Comment(Entity):
    likes = GenericRelation(Activity)
