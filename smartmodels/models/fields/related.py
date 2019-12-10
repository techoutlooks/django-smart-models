from django.db import models
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor


class SmartReverseOneToOneDescriptor(ReverseManyToOneDescriptor):
    def __get__(self, instance, cls=None):
        objects = super(SmartReverseOneToOneDescriptor, self).__get__(instance, cls)
        return objects.first()


class SmartOneToOneField(models.OneToOneField):
    """
    Experimental.

    A ForeignKey field that work on only the top/first instance,
    emulating a OneToOneField with regard to the cardinality of objects (==1),
    but still providing for the storage of many instance of the related model vs. the remote model.
    """

    related_accessor_class = SmartReverseOneToOneDescriptor
