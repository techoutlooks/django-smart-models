"""
Smart Serializers!
"""
import copy
from collections import defaultdict

from rest_framework.serializers import BaseSerializer, ListSerializer
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
from rest_framework.generics import get_object_or_404

from smartmodels.exceptions import NestingErrorException


BLACKLISTED_VALIDATORS = [UniqueValidator, UniqueTogetherValidator]


class WritableNestingModelSerializerMixin(object):
    """
    ModelSerializer Mixin for automating working with writable nested serializers.
    It performs at once, out of the same data, a single CRUD operation on nested fields.

    (*)
    (*) Allows for providing a custom behavior for every child (by implementing `get_nested_instance()`) eg.
        looking up foreign models, without hitting by default the UniqueValidator or UniqueTogetherValidator exceptions.
    (*) Inhibits on demand the uniqueness validators on embedded serializers (ie. `requires_custom_validation` is True),
        keeping validators other than the BLACKLISTED_VALIDATORS.
    (*) Recognizes flatten representations of the embedded serializers (`data=` attribute), as well as the nested.
    (*) Fallback to the default Serializer class's behavior if exclude_nested = '__all__' is set on the metaclass.
    (*) Handles instantiation with many=True, with DRF replacing under the scene this serializer by a ListSerializer
        instance, setting us as a mere `child`.
        rtd@ https://www.django-rest-framework.org/api-guide/serializers/#listserializer

    Discussions abt writable nested serializers:
        # http://www.django-rest-framework.org/api-guide/validators/#updating-nested-serializers.
        # https://stackoverflow.com/questions/25026034/django-rest-framework-modelserializer-get-or-create-functionality
        # https://groups.google.com/forum/#!msg/django-rest-framework/Wo70bMsKQAg/YDAFpFmwsqwJ

    Example Usage (1):
    Save the nested fields at once, keeping the unique constraint validators enabled
    for the fields: 'exclude_field_1', 'exclude_field_1'

        class AccountSerializer(WritableNestingModelSerializerMixin, serializers.ModelSerializer):
            owner = UserSerializer(many=False, required=False)
            class Meta:
                model = Account
                fields = '__all__'
                exclude_nested = ['exclude_field_1', 'exclude_field_2']

    Example Usage (2):
    Save the nested fields at once, enabling custom validation on all fields (exclude_nested=[] or not specified,
    the default). In this case, implementing your custom behaviour in the `get_nested_instance()` callback is
    mandatory for all non-excluded fields.

        class AccountSerializer(WritableNestingModelSerializerMixin, serializers.ModelSerializer):
            owner = UserSerializer(many=False, required=False)
            class Meta:
                model = Account
                fields = '__all__'

            def get_nested_instance(self, field, validated_data):
                if field == 'owner':
                    username = validated_data.pop('username')
                    owner, created = get_user_model().objects.get_or_create(username=username, defaults=validated_data)
                    if 'password' in validated_data:
                        password = validated_data.pop('password')
                        owner.set_password(password)
                    for (f, v) in validated_data.items():
                        setattr(owner, f, v)
                    owner.save()
                    return owner
    """
    # TODO: is good thing to recognize a flatten representation of nested data, mixed with `this` data?
    # TODO: get_nested_instance() --> self.instance override
    # TODO: Write tests.
    # TODO: Contribute
    #   https://medium.com/django-rest-framework/dealing-with-unique-constraints-in-nested-serializers-dade33b831d9

    # for internal use only
    _nested = {}                    # the nested serializers
    _nesting_model_fields = {}      # the nesting model's attributes ready for saving to db

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
    def nesting_model_fields(self):
        if self._nesting_model_fields:
            return self._nesting_model_fields
        return self.get_nesting_model_fields()

    @property
    def nested_custom(self):
        """
        Subset of the nested serializers that require custom validation (The nested minus the excluded).
        Their validators should be inhibited and lookups of related instances be provided for explicitly,
        through the `get_nested_instance()`. `is_valid()` sets raise_exception=False for such fields.
        """
        custom = self.nested
        exclude_nested = getattr(getattr(self, 'Meta'), 'exclude_nested', [])
        excluded = set(self.nested) if exclude_nested == '__all__' else set(exclude_nested)
        for name in excluded:
            del custom[name]
        return custom

    # The name of nested fields not eligible for custom validation.
    # Set `exclude_nested='__all__'` for fallback to DRF's default behaviour (unique constraint validators on).
    # The default DRF behaviour implies that unique constraints validators should NOT be disabled,
    # and the `disable_nested_validators()` callback be subsequently called, giving the api user a chance
    # to provide for a custom lookup of related model instances using `get_nested_instance()`.
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
        obj, created = self.Meta.model.objects.get_or_create(**self.nesting_model_fields)
        return obj

    def is_valid(self, raise_exception=False):
        """
        We hook on to disable uniqueness validators on nested serializers fields (those meant for customizing),
        allowing the application's custom behavior to be injected in `get_nested_instance()`
        `raise_exception` should be left to False.
        """
        for name, field in self.nested_custom.items():
            if isinstance(field, ListSerializer):
                continue
            self.disable_validators(field)
            raise_exception = False

        return super(WritableNestingModelSerializerMixin, self).is_valid(raise_exception)

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
            requires_custom_validation = (name in list(self.nested_custom))

            # only pick up that subset of data that pertain to serializer, hence getting ready for saving
            # through the ORM. it is available as serializer.data after calling `is_valid()`, no matter if
            # the validation failed.
            serializer.is_valid(raise_exception=not requires_custom_validation)

            # unless a custom behaviour is sought (by defining the `get_nested_instance()` method),
            # persist nested data using the ORM directly, by trusting the serializer's create() and update()
            # specialized methods. serializer.save() indeed won't succeed due to data possibly not being valid.
            # default behaviour is inspired by the BaseSerializer's save() method.
            child_data = serializer.data
            if self.instance is not None:
                obj = getattr(self.instance, name)
                obj = self.get_nested_instance(name, child_data) if requires_custom_validation \
                    else serializer.update(obj, child_data)
                assert obj is not None, (
                    '`update()` did not return an object instance for field: {field}.'
                    'Do you have custom validation enabled without explicitly defining `get_nested_instance()`?'
                    .format(field=serializer)
                )
            else:
                obj = self.get_nested_instance(name, child_data) if requires_custom_validation \
                    else serializer.create(child_data)
                assert obj is not None, (
                    '`create()` did not return an object instance for field: {field}'
                    'Do you have custom validation enabled without explicitly defining `get_nested_instance()`?'
                    .format(field=serializer)
                )

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
        Return bound instances (from the same `data`) of all nested serializers,
        as a dictionary of {field_name: bound_serializer_instance} items.

        Also recognizes flatten data representation of the nested fields.
        """
        nested_serializers = {}

        for name, field in super(WritableNestingModelSerializerMixin, self).get_fields().items():
            if isinstance(field, BaseSerializer):
                sz_cls = type(field)
                data_for_field = copy.deepcopy(data.get(name, None) or data)  # nested json or not?
                field_opts = {}

                # "When a serializer is instantiated and many=True is passed, a ListSerializer instance will be created.
                # The serializer class then becomes a child of the parent ListSerializer", rtd. for ListSerializer
                if isinstance(field, ListSerializer):
                    field_opts.update(child=field.child.__class__())

                serializer = sz_cls(data=data_for_field, **field_opts)
                nested_serializers.update({name: serializer})

        return nested_serializers

    def get_nesting_model_fields(self):
        """
        Extract a dict of valid model attributes from the validated data.
        eg. in subsequent call to model.objects.save(**model_params), for creating a model instance
        """
        writable_nested = [sz for sz in self.save_nested() if sz.read_only]

        # purge validated data from deserialized nested objects,
        # leaving validated_data with fields from this (parent) serializer only.
        model_fields = self._validated_data
        for field in list(writable_nested):
            if field in model_fields:
                del model_fields[field]

        # re-embed the nested fields,
        # this time as serialized objects instead.
        return dict(list(model_fields.items()) + list(writable_nested.items()))

    def get_nesting_instance(self, **opts):
        assert hasattr(self, 'initial_data'), (
            'Cannot call `.is_valid()` as no `data=` keyword argument was '
            'passed when instantiating the serializer instance.'
        )

        ModelClass = self.Meta.model
        instance = get_object_or_404(ModelClass.objects.all(), dict(self.nesting_model_fields, **opts))
        return instance

    def disable_validators(self, field):
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
        meta = getattr(field, 'Meta', None)
        extra_kwargs = getattr(meta, 'extra_kwargs', defaultdict(dict))

        for (_name, _field) in field.get_fields().items():
            extra_kwargs[_name] = {'validators': self.filter_nested_validators(_field, BLACKLISTED_VALIDATORS)}
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

            # re-insert back the flatten data that corresponds to each child field
            # as nested serialized representations
            for name, child in self.nested.items():
                if name not in validated_data:
                    validated_data[name] = child.validated_data

        except Exception as e:
            msg = "is_valid() probably not called on child serializers ..."
            raise NestingErrorException(e, msg=msg)
