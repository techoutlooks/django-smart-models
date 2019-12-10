# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from smartmodels.admin.mixins import ResourceAdminMixin
from .models import Activity


class ActivityAdmin(ResourceAdminMixin, admin.ModelAdmin):
    pass


admin.site.register(Activity, ActivityAdmin)
