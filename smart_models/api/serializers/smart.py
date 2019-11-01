from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from .mixins import WritableNestingSerializerMixin
from ...models.shared import get_namespace_model


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email',)
        extra_kwargs = {'password': {'write_only': True}}


class SmartUserSerializer(serializers.ModelSerializer):
    """
    Will supply the smart user fields, ie. `created_by`, `updated_by`, `deleted_by`
    for all AbstractSmartModelSerializer subclasses.
    """

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email',)
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        obj, created = self.Meta.model.objects.get_or_create(**validated_data)
        return obj


class AbstractSmartModelSerializer(WritableNestingSerializerMixin, serializers.ModelSerializer):
    """
    Not for instantiating.
    Subclass for builtin support for smart models (ie. AbstractSmartModel subclasses)
    """

    user = SmartUserSerializer()
    created_by = SmartUserSerializer(required=False)
    updated_by = SmartUserSerializer(required=False)
    deleted_by = SmartUserSerializer(required=False)

    class Meta:
        exclude_nested = ('user',)
        abstract = True

    def get_nested_instance(self, field, child_data):
        if field in ('created_by', 'updated_by', 'deleted_by'):
            return get_object_or_404(get_user_model(), **child_data)
        return None


class SmartOwnerSerializer(serializers.ModelSerializer):
    """
    Experimental.

    Serializer for nesting the `owner` field available on SharedResource's.
    10
    2) Defaults to the sentinel user if Meta.model = settings.AUTH_USER_MODEL.

    """
    class Meta:
        model = get_namespace_model()
        fields = '__all__'
