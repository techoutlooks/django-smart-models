from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from .mixins import WritableNestingModelSerializerMixin
from smartmodels.models.resource import get_namespace_model


class OwnerSerializer(serializers.ModelSerializer):
    """
    Will supply the smart owner fields, ie. `created_by`, `updated_by`, `deleted_by`
    for all SmartModelSerializer subclasses.
    """

    class Meta:
        model = get_user_model()
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        obj, created = self.Meta.model.objects.get_or_create(**validated_data)
        return obj


class SmartModelSerializer(serializers.ModelSerializer):
    """
    Not for instantiating.
    Subclass for builtin support for smart models (ie. SmartModel subclasses)
    """

    owner = OwnerSerializer(read_only=True)
    created_by = OwnerSerializer(read_only=True)
    updated_by = OwnerSerializer(read_only=True)
    deleted_by = OwnerSerializer(read_only=True)

    class Meta:
        exclude_nested = ('owner',)
        abstract = True

    def get_nested_instance(self, field, child_data):
        if field in ('created_by', 'updated_by', 'deleted_by'):
            return get_object_or_404(get_user_model(), **child_data)
        return None


class NamespaceSerializer(serializers.ModelSerializer):
    """
    Experimental.

    Writable serializer for nesting the `owner` field available on resources.
    Nota: Defaults to the sentinel user if Meta.model = settings.AUTH_USER_MODEL.

    """
    class Meta:
        model = get_namespace_model()
        fields = '__all__'


class ResourceSerializer(SmartModelSerializer):
    namespaces = NamespaceSerializer(read_only=True, many=True, required=False)
