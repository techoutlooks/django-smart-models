"""
Smart Serializers!
"""

from collections import defaultdict

from rest_framework.serializers import BaseSerializer
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
from rest_framework.generics import get_object_or_404

from ..exceptions import NestingErrorException


BLACKLISTED_VALIDATORS = [UniqueValidator, UniqueTogetherValidator]


class WritableNestingSerializerMixin(object):
    """
    Serializer Mixin for automating working with writable nested serializers:

    (*) Perform custom operations at once on nested serializers
    (*) Allows for providing a custom behavior for every child (by implementing `get_nested_instance()`) eg.
        looking up foreign models, without hitting by default the UniqueValidator or UniqueTogetherValidator exceptions.
    (*) Inhibits on demand (`custom_validation` boolean) all uniqueness validators on embedded serializers.
        Keeps validators other than BLACKLISTED_VALIDATORS.
    (*) Recognizes flatten representations of the embedded serializers (`data=` attribute), as well as the nested.
    (*) Fallback to the default Serializer class's behavior if exclude_nested = '__all__' requested, yet

    Discussions:
        # http://www.django-rest-framework.org/api-guide/validators/#updating-nested-serializers.
        # https://stackoverflow.com/questions/25026034/django-rest-framework-modelserializer-get-or-create-functionality
        # https://groups.google.com/forum/#!msg/django-rest-framework/Wo70bMsKQAg/YDAFpFmwsqwJ

    Example Usage (1):
    Auto save nested fields, but leaving unique constraint validators enabled.

        class AccountSerializer(WritableNestingSerializerMixin, serializers.ModelSerializer):
            user = UserSerializer(many=False, required=False)
            class Meta:
                model = Account
                fields = '__all__'
                exclude_nested = fields

    Example Usage (2):
    Auto save nested fields, disabling custom validation.
    In this case implementing your custom behaviour in the `get_nested_instance()` callback is mandatory.

        class AccountSerializer(WritableNestingSerializerMixin, serializers.ModelSerializer):
            user = UserSerializer(many=False, required=False)
            class Meta:
                model = Account
                fields = '__all__'

            def get_nested_instance(self, field, validated_data):
                if field == 'user':
                    username = validated_data.pop('username')
                    user, created = get_user_model().objects.get_or_create(username=username, defaults=validated_data)
                    if 'password' in validated_data:
                        password = validated_data.pop('password')
                        user.set_password(password)
                    for (f, v) in validated_data.items():
                        setattr(user, f, v)
                    user.save()
                    return user
    """
    # TODO: is good thing to recognize a flatten representation of nested data, mixed with `this` data?
    # TODO: get_nested_instance() --> self.instance override
    # TODO: Write tests.
    # TODO: Contribute
    #   https://medium.com/django-rest-framework/dealing-with-unique-constraints-in-nested-serializers-dade33b831d9

    # for internal use only
    _nested = {}                    # the nested serializers
    _nesting_model_params = {}      # the nesting model's attributes ready for saving to db

    @property
    def nested(self):
        """
        The nested serializers initialized with data,
        as a dictionary of {field_name: serializer_instance} items.
        """
        if self._nested:
            return self._nested
        nested = self.get_nested(self.initial_data)
        return nested

    @nested.setter
    def nested(self, value):
        self._nested = value

    @property
    def nesting_model_params(self):
        if self._nesting_model_params:
            return self._nesting_model_params
        return self.get_nesting_model_params()

    @property
    def nested_custom(self):
        """
        Subset of the nested serializers that require custom validation (The nested minus the excluded).
        Their validators should be inhibited and,
        custom instances lookups provided for, through the `get_nested_instance()`.
        """
        custom = self.nested
        exclude_nested = getattr(getattr(self, 'Meta'), 'exclude_nested', [])
        excluded = set(self.nested) if exclude_nested == '__all__' else set(exclude_nested)
        for name in excluded: del custom[name]
        return custom

    # name of nested serializers to exclude from custom validation,
    # ie., leave default framework validation as is.
    # do not disable the unique validators constraints thereof (`disable_nested_validators()` not called),
    # nor consider them for custom lookup (`get_nested_instance()`)
    # set to '__all__' for fallback to default behaviour (unique constraint validators are on).
    exclude_nested = []

    def create(self, validated_data):
        """
        Persist deserialized fields including all nested objects (writable nested serializers) to db.

        Override of the create() method that relies on the specified custom behavior `get_nested_instance()`
        for obtaining every nested object from validated data.

        :param validated_data:
        :return: saved object
        """

        # create (enforce unique constraint check on parent serializer too?) update_or_create?
        obj, created = self.Meta.model.objects.get_or_create(**self.nesting_model_params)
        return obj

    def is_valid(self, raise_exception=False):
        """
        We hook on to disable uniqueness validators on nested serializers fields (those meant for customizing),
        allowing the application's custom behavior to be injected in `get_nested_instance()`
        `raise_exception` should be left to False.
        """
        for (name, serializer) in self.nested_custom.items():
            self.disable_nested_validators(serializer)
        return super(WritableNestingSerializerMixin, self).is_valid(raise_exception)

    def save_nested(self, **kwargs):
        """
        Return saved instances of nested serializers
        as an iterable of {serializer_field: nested_model_instance} items.

        Let each nested serializer to pick his own dataset from entire validated_data
        and persist that data to disk, performing custom validation on saving if requested.

        When custom validation is set, responsibility for returning a valid object ready for
        saving is delegated to `get_nested_instance()`.
        """
        assert hasattr(self, 'initial_data'), (
            'Cannot call `.save_nested()` as no `data=` keyword argument was '
            'passed when instantiating the serializer instance.'
        )

        instances = {}

        # loop through all nested serializers,
        # run custom object lookup on child (`get_nested_instance`) only if expressly requested
        for (name, serializer) in self.nested.items():
            is_custom_validation = (name in list(self.nested_custom))

            # only pick up that subset of data that pertain to serializer, hence getting ready for saving
            # through the ORM. it is available as serializer.data after calling `is_valid()`, no matter if
            # the validation failed.
            serializer.validate_survey(raise_exception=not is_custom_validation)

            # unless a custom behaviour is sought (by defining the `get_nested_instance()` method),
            # persist nested data using the ORM directly, by trusting the serializer's create() and update()
            # specialized methods. serializer.save() indeed won't succeed due to data possibly not being valid.
            # default behaviour is inspired by the BaseSerializer's save() method.
            child_data = serializer.data
            if self.instance is not None:
                obj = getattr(self.instance, name)
                obj = self.get_nested_instance(name, child_data) if is_custom_validation \
                    else serializer.update(obj, child_data)
                assert obj is not None, '`update()` did not return an object instance.'
            else:
                obj = self.get_nested_instance(name, child_data) if is_custom_validation \
                    else serializer.create(child_data)
                assert obj is not None, '`create()` did not return an object instance.'

            instances.update({name: obj})

        return instances

    def get_nested_instance(self, field, child_data):
        """
        Per-nested serializer customizable callback.
        Defines a custom behaviour to be run with each nested serializer (only those meant for customization),
        since the default implementation will enforce uniqueness validators checks
        http://www.django-rest-framework.org/api-guide/validators/#updating-nested-serializers

        For returning proper object to be used for saving (update or create) this field's data.
        This is typical use case where we need to skip validation (eg. avoid `IntegrityError: UNIQUE constraint failed`),
        since normal validation for a nested serializer is anticipated to fail.
        Left to the user for implementation.

        :param field: nested serializer whose instance we want to return
        :param child_data: serialized data from `field`.
        :return:
        """
        raise NotImplementedError('`get_nested_instance()` must be implemented.')

    def get_nested(self, data):
        """
        Return initialized instances (from the same `data`) of all nested serializers,
        as a dictionary of {field_name: serializer_instance} items.

        Also recognizes flatten data representation of the nested fields.
        """
        nested_serializers = {}

        for name, field in super(WritableNestingSerializerMixin, self).get_fields().items():
            if isinstance(field, BaseSerializer):
                sz_cls = type(field)
                data_for_field = data.get(name, None) or data  # nested json or not?
                serializer = sz_cls(data=data_for_field)
                nested_serializers.update({name: serializer})

        return nested_serializers

    def get_nesting_model_params(self):
        """
        Return a dict of valid model attributes for creating a model instance,
        eg. in subsequent call to model.objects.save(**model_params).
        """
        nested_objects = self.save_nested()

        # purge validated data from deserialized nested objects,
        # leaving validated_data with fields from this (parent) serializer only.
        model_params = self._validated_data
        for field in list(nested_objects):
            if field in model_params:
                del model_params[field]

        # re-embed the nested fields,
        # this time as serialized objects instead.
        return dict(list(model_params.items()) + list(nested_objects.items()))

    def get_nesting_instance(self, **opts):
        assert hasattr(self, 'initial_data'), (
            'Cannot call `.is_valid()` as no `data=` keyword argument was '
            'passed when instantiating the serializer instance.'
        )

        ModelClass = self.Meta.model
        instance = get_object_or_404(ModelClass.objects.all(), dict(self.nesting_model_params, **opts))
        return instance

    def disable_nested_validators(self, child):
        """
        Disable unique constraint validators on every field on the `child` serializer,
        by setting each child's `extra_kwargs` like so:

        class NestedSerializer1(Serializer):
            ...
            class Meta:
                extra_kwargs = {
                    'unique_field_name_1': {'validators': [..]},
                    'unique_field_name_2': {'validators': [..]}
                }
        """
        meta = getattr(child, 'Meta', None)
        extra_kwargs = getattr(meta, 'extra_kwargs', defaultdict(dict))

        for (name, field) in child.get_fields().items():
            extra_kwargs[name] = {'validators': self.filter_nested_validators(field, BLACKLISTED_VALIDATORS)}
        setattr(meta, 'extra_kwargs', extra_kwargs)

    @staticmethod
    def filter_nested_validators(field, blacklist):
        """
        Filters unique constraint validators out of given field.
        """
        for_disabling = lambda v: any([isinstance(v, d) for d in blacklist])
        return list(filter(lambda v: not for_disabling(v), field.validators))


class FlatNestingSerializerMixin(object):
    """
    Experimental.
    For recognizing flatten data representation of objects,
    as well as the nested.
    """

    @property
    def validated_data(self):
        """
        self.data, but also recognizes flatten serialized representation of the nested fields.
        :return:
        """
        try:
            validated_data = super(FlatNestingSerializerMixin, self).validated_data

            # re-insert the flatten data that belongs each child
            # as nested serialized representations
            for name, child in self.nested.items():
                if name not in validated_data:
                    validated_data[name] = child.validated_data

        except Exception as e:
            msg = "is_valid() probably not called on child serializers ..."
            raise NestingErrorException(e, msg=msg)
