# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from smartmodels.admin.mixins import ResourceAdminMixin
from .models import Post, Question, Answer, Comment


class PostAdmin(ResourceAdminMixin, admin.ModelAdmin):
    pass


class QuestionAdmin(ResourceAdminMixin, admin.ModelAdmin):
    pass


class AnswerAdmin(ResourceAdminMixin, admin.ModelAdmin):
    pass


class CommentAdmin(ResourceAdminMixin, admin.ModelAdmin):
    pass


admin.site.register(Post, PostAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(Comment, CommentAdmin)

