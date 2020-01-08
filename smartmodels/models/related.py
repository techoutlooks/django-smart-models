# -*- coding: utf-8 -*-
"""
Helpers to work with django models.

"""
import django
from django.utils.translation import ugettext_lazy as _
# FIXME: re-enable requires Django>=2.0 below, was disable for integration tests vs msg7
# assert django.VERSION >= (2, 0), _("Requires Django>=2.0")


from django.db import models
from django.db.models import Q


class ModelFactoryMixin(object):
    """
    Convenience methods for working with fields and values of this model
    """

    @classmethod
    def parse_model_data(cls, exclude=[], **data):
        """
        Filter out any data that do not belong to this model,
        or set explicitly for excluding
        """
        for prop in data.keys():
            if prop not in [f.name for f in cls._meta.fields] or prop in exclude:
                data.pop(prop)
        return data

    @classmethod
    def get_related_managers(cls):
        """ Get property names for all related objects """
        return [getattr(cls, rel.get_accessor_name()) for rel in cls._meta.get_all_related_objects()]


class ForeignModelFactoryMixin(ModelFactoryMixin):
    """
    Convenience methods for working with related (foreign) models that relate to this model.
    Currently only supports subclasses of ForeignKey (eg. ForeignKey, OneToOneField).
    """

    @staticmethod
    def get_fk_model(model, fieldname):
        """
        returns None if not ForeignKey, otherwise the relevant model
        """
        field_object = model._meta.get_field(fieldname)
        if isinstance(field_object, models.ForeignKey):
            return field_object.related_model
        return None

    @classmethod
    def get_related_models(cls):
        """
        Get all foreign models as a hash
        """
        return filter(None, [cls.get_fk_model(cls._meta.model, f) for f in [f.name for f in cls._meta.fields]])

    @classmethod
    def get_fk_fields(cls):
        """
        Return classes for any ForeignKey or OneToOneField relation found on this model.
        """
        fk_fields = []
        for field in cls._meta.fields:
          if field.get_internal_type() == models.ForeignKey:
            fk_fields.append(field)
        return fk_fields

    @classmethod
    def filter_related(cls, fk_name, **kwargs):
        """
        Return the QuerySet of this model that matches the criteria posed on instances from the related (parent).
        Given a fk field name, will follow that relation to find all remote instances that matches kwargs.
        """
        # assert not isinstance(kwargs, dict), _("Wrong 'kwargs'! Expected keys/values, passed dict")
        opts = {}

        for prop in kwargs.keys(): opts.update({"{}__%s".format(fk_name) % prop: kwargs.get(prop)})
        # print("filter_related:: model=%s fk_name=%s opts=%s" % (cls, fk_name, opts))
        qs = cls.objects.filter(Q(**opts))
        # print("filter_related:: objects=%s" % qs)

        return qs
