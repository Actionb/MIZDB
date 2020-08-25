# WARNING: unique together options are not really supported. Use with caution.
import itertools
import factory
import sys
from stdnum import issn

import DBentry.models as _models
from DBentry.utils import is_iterable, get_model_relations, get_model_fields


class RuntimeFactoryMixin(object):
    """
    A mixin that can create a related factory on the fly.

    Accepts the additional keyword argument 'related_model' which is the model
    class for the related factory.
    """

    def __init__(self, *args, **kwargs):
        self.related_model = kwargs.pop('related_model', None)
        self._factory = None
        super().__init__(*args, **kwargs)

    @property
    def factory(self):
        if self._factory is None:
            try:
                self._factory = super().get_factory()
            except AttributeError:
                # The related factory does not exist yet.
                if self.related_model is None:
                    raise AttributeError(
                        'Missing related factory for {}'.format(self.name)
                    )
                self._factory = modelfactory_factory(self.related_model)
        return self._factory

    def get_factory(self):
        return self.factory


class UniqueFaker(factory.Sequence):
    """
    A faker that returns unique values by using sequences.

    Parameters:
        - faker (str or a factory.Faker instance): the faker or the name of a
            faker provider to use
        - function: the factory sequence callable that returns the suffix that
            makes the value unique; defaults to lambda n: n
    Only works for strings.
    """

    def __init__(self, faker, function=None, **kwargs):
        if function is None:
            function = lambda n: n
        super().__init__(function, **kwargs)
        self.faker = faker
        if isinstance(faker, str):
            # A provider name was passed in.
            self.faker = factory.Faker(faker)

    def evaluate(self, instance, step, extra):
        n = super().evaluate(instance, step, extra)
        return self.faker.generate(extra) + str(n)


class ISSNFaker(factory.Faker):
    """A faker that provides valid ISSN numbers."""

    def __init__(self, provider='ean', **kwargs):
        super().__init__(provider, **kwargs)

    def generate(self, extra_kwargs):
        ean = super().generate(extra_kwargs)
        return ean[3:-3] + issn.calc_check_digit(ean[3:-3])


class SubFactory(RuntimeFactoryMixin, factory.SubFactory):
    """A SubFactory that only generates objects if required."""

    def __init__(self, factory, required=False, **kwargs):
        self.required = required
        super().__init__(factory, **kwargs)

    def evaluate(self, instance, step, extra):
        # Do not generate an object unless required or parameters are declared
        # in extra.
        if not self.required and not extra:
            return None
        # evaluate() is called while resolving the pre-declarations of a factory.
        # 'extra' contains explicitly passed in parameters - the factory needs to
        # know these when deciding on what fields to query for in get_or_create.
        self.factory.set_memo(list(extra.keys()))
        return super().evaluate(instance, step, extra)


class SelfFactory(SubFactory):
    """A SubFactory used for recursive relations."""

    def evaluate(self, instance, step, extra):
        # 'extra' may define the recursion depth:
        # extra = {field__field__field=None}
        # If 'extra' is empty and the model field is required, the recursion
        # should happen exactly once.
        if self.required and not extra:
            # Recurse once by adding 'itself: None' to extra.
            self_name = ''
            for k, v in self.factory._meta.pre_declarations.as_dict().items():
                if v == self:
                    self_name = k
                    break
            if not self_name:
                # Do not recurse at all, if the SelfFactory cannot 'find itself'
                # in the factory's declarations.
                return None
            extra = {self_name: None}
        return super().evaluate(instance, step, extra)


class RelatedFactory(RuntimeFactoryMixin, factory.RelatedFactory):
    """
    A related factory that can handle iterables passed in.

    Accepts two additional keyword arguments:
        - accessor_name (str): the name of the instance's attribute that refers
            to the relation's descriptor.
        - extra (int): the number of extra objects to create in addition to the
            objects that result from the passed in kwargs.

    Example:
        class BuchFactory():
            autor = RelatedFactory(AutorFactory,'buch')
        BuchFactory(
            autor__name=['Alice','Bob','Charlie'],
            autor__kuerzel=['Al','Bo'],
            autor__beschreibung = 'Test'
        )
        results in three calls to AutorFactory where context.extra is: {
            'name':['Alice','Bob','Charlie'],
            'kuerzel':['Al','Bo'],
            'beschreibung':'Test'
        }
        => AutorFactory(name='Alice', kuerzel='Al', beschreibung='Test')
        => AutorFactory(name='Bob', kuerzel='Bo', beschreibung='Test')
        => AutorFactory(name='Charlie', beschreibung='Test')
    """

    def __init__(self, factory, factory_related_name='', accessor_name=None,
            extra=0, **defaults):
        self.accessor_name = accessor_name
        self.extra = extra
        super().__init__(factory, factory_related_name, **defaults)

    def call(self, instance, step, context):
        factory = self.get_factory()
        related_objects = []

        if context.value:
            # context.value contains the related_object(s) that should be added
            # to instance.
            if isinstance(context.value, (list, tuple)):
                # Force tuples into lists:
                related_objects = list(context.value)
            else:
                related_objects = [context.value]
            if self.accessor_name and hasattr(instance, self.accessor_name):
                getattr(instance, self.accessor_name).add(*related_objects)

        if context.extra or self.extra:
            # From the class doctstring example:
            # context.extra = {
            #    'name': ['Alice','Bob','Charlie'],
            #    'kuerzel': ['Al','Bo'],
            #    'beschreibung':'Test'
            # }
            extra = self.extra
            if 'extra' in context.extra:
                extra = context.extra.pop('extra')

            passed_kwargs = []
            default_kwargs = dict(self.defaults)
            if self.name:
                default_kwargs[self.name] = instance

            if context.extra:
                if any(is_iterable(v) for v in context.extra.values()):
                    # Separate items in extra that are iterables from those
                    # that are not.
                    iterables = {
                        # e.g.: {'name': ['Alice','Bob','Charlie'], 'kuerzel': ['Al','Bo']}
                        k: v for k, v in context.extra.items()
                        if is_iterable(v)
                    }
                    singles = {
                        # e.g.: {'beschreibung': 'Test'}
                        k: v for k, v in context.extra.items()
                        if k not in iterables
                    }
                    # Create keyword arguments for the all related instances
                    # expected to be created from the iterables, sublementing
                    # missing values with None (zip_longest).
                    # e.g: [('Alice','Al'), ('Bob','Bo'),('Charlie',None)]
                    for value in itertools.zip_longest(*iterables.values()):
                        kwargs = default_kwargs.copy()
                        kwargs.update(singles)
                        kwargs.update({
                            k: v for k, v in zip(iterables.keys(), value)
                            if v is not None
                        })
                        passed_kwargs.append(kwargs)
                else:
                    # None of the values are iterables.
                    # Only one related instance is going to be created.
                    kwargs = default_kwargs.copy()
                    kwargs.update(context.extra)
                    passed_kwargs.append(kwargs)
            # Handle the 'extra' argument;
            # add default kwargs for every extra instance to be created.
            while extra > 0:
                passed_kwargs.append(default_kwargs)
                extra -= 1
            # Create the related instances.
            for kwargs in passed_kwargs:
                related_objects.append(step.recurse(factory, kwargs))
        return related_objects


class M2MFactory(RelatedFactory):
    """
    A factory that implements a m2m relation with the added benefits of
    RelatedFactory.

    Parameters:
        descriptor_name (str): the name of the instance's attribute that refers
            to the relation's descriptor.
    """

    def __init__(self, factory, descriptor_name=None, **defaults):
        self.descriptor_name = descriptor_name
        if 'accessor_name' in defaults:
            # Having the attribute accessor_name upon calling super().call()
            # will make the RelatedFactory try to invoke .add() which is not
            # allowed for intermediary tables that were not auto_created.
            del defaults['accessor_name']
        super().__init__(factory, **defaults)

    def call(self, instance, step, context):
        related_manager = getattr(instance, self.descriptor_name)
        # Get the right field names from the intermediary m2m table.
        source_field = related_manager.through._meta.get_field(
            related_manager.source_field_name
        )
        if isinstance(instance, source_field.related_model):
            # The source_field points to the instance's model.
            source = related_manager.source_field_name
            target = related_manager.target_field_name
        else:
            source = related_manager.target_field_name
            target = related_manager.source_field_name

        # Add the relation.
        for related_object in super().call(instance, step, context):
            related_manager.through.objects.create(
                **{source: instance, target: related_object}
            )


class MIZDjangoOptions(factory.django.DjangoOptions):

    def _get_factory_name_for_model(self, model):
        """Return the probable factory name for a given model."""
        class_name = model.__name__.replace(
            'm2m_', '').replace('_', ' ').title().replace(' ', '')
        return self.factory.__module__ + '.' + class_name + 'Factory'

    @staticmethod
    def _get_decl_for_model_field(field):
        """For a given model field, return an appropriate faker declaration."""
        try:
            from DBentry.fields import PartialDateField
            if isinstance(field, PartialDateField):
                return factory.Faker('date')
        except ImportError:
            pass
        internal_type = field.get_internal_type()
        if internal_type in ('CharField', 'TextField'):
            if field.unique:
                declaration = UniqueFaker('word')
            else:
                declaration = factory.Faker('word')
        elif internal_type in (
                'IntegerField', 'PositiveSmallIntegerField', 'SmallIntegerField',
                'BigIntegerField'):
            if field.unique:
                declaration = factory.Sequence(lambda n: n)
            else:
                declaration = factory.Faker('pyint')
        elif internal_type in ('BooleanField', 'NullBooleanField'):
            declaration = factory.Faker('pybool')
        elif internal_type in ('DateField', 'DateTimeField', 'TimeField'):
            # The providers for these fields are called 'date','date_time','time'.
            # Derive the provider name from the internal_type.
            provider = ''
            for i, c in enumerate(internal_type.replace('Field', '')):
                if i and c.isupper():
                    provider += '_'
                provider += c.lower()
            declaration = factory.Faker(provider)
        elif internal_type == 'DurationField':
            declaration = factory.Faker('time_delta')
        return declaration

    def add_base_fields(self):
        """
        Add any fields of the model that are not a relation and require a value.
        """
        for field in get_model_fields(self.model, foreign=False, m2m=False):
            if hasattr(self.factory, field.name) or field.has_default() or field.blank:
                continue
            setattr(
                self.factory, field.name, self._get_decl_for_model_field(field)
            )

    def add_m2m_factories(self):
        """Add M2MFactories for every many to many relation of this model."""
        for rel in get_model_relations(self.model):
            if not rel.many_to_many:
                continue
            if self.model == rel.field.model:
                # The ManyToManyField is declared on model.
                related_model = rel.field.related_model
                descriptor_name = rel.field.name
                declaration_name = rel.field.name
            elif self.model == rel.field.related_model:
                # The ManyToManyField is declared on the related_model;
                # working on a 'reverse' m2m relation
                related_model = rel.field.model
                descriptor_name = rel.get_accessor_name()
                declaration_name = rel.name
            else:
                # Rel is an inherited relation as neither end of the relation
                # points to self.model.
                # One relation points to the inherited parent model, the other
                # to the actual related model. If rel.field.model is the parent,
                # the related_model is rel.field.related_model and vice versa.
                if rel.field.model in self.model._meta.parents:
                    # self.model inherited the actual ManyToManyField.
                    # Use the inherited ManyToManyField's name for descriptor
                    # and declaration.
                    related_model = rel.field.related_model
                    descriptor_name = rel.field.name
                    declaration_name = rel.field.name
                elif rel.field.related_model in self.model._meta.parents:
                    # self.model inherited the reverse ManyToManyRelation
                    related_model = rel.field.model
                    descriptor_name = rel.get_accessor_name()
                    declaration_name = rel.name
                else:
                    raise TypeError(
                        "Unknown relation: {!s}".format(rel.get_path_info())
                    )
            factory_name = self._get_factory_name_for_model(related_model)
            if not hasattr(self.factory, declaration_name):
                m2m_factory = M2MFactory(
                    factory_name,
                    descriptor_name=descriptor_name,
                    related_model=related_model
                )
                setattr(self.factory, declaration_name, m2m_factory)

    def add_related_factories(self):
        """
        Add RelatedFactories for every one to many (i.e. reverse) relation of
        this model.
        """
        for rel in get_model_relations(self.model, forward=False):
            if rel.many_to_many:
                continue
            # These are all reverse relations, meaning rel.model == self.model.
            factory_name = self._get_factory_name_for_model(rel.related_model)
            accessor_name = rel.get_accessor_name()
            if not hasattr(self.factory, rel.name):
                related_factory = RelatedFactory(
                    factory_name,
                    factory_related_name=rel.field.name,
                    accessor_name=accessor_name,
                    related_model=rel.related_model
                )
                setattr(self.factory, rel.name, related_factory)

    def add_sub_factories(self):
        """
        Add SubFactories for every (forward) one to many relation of this model.
        """
        for field in get_model_fields(self.model, base=False, foreign=True, m2m=False):
            if not hasattr(self.factory, field.name):
                factory_name = self._get_factory_name_for_model(field.related_model)
                if field.related_model == self.model:
                    _factory = SelfFactory(self.factory, required=not field.null)
                else:
                    _factory = SubFactory(
                        factory_name,
                        related_model=field.related_model,
                        required=not field.null
                    )
                setattr(self.factory, field.name, _factory)

    def contribute_to_class(self, factory_class, meta=None, base_meta=None,
                            base_factory=None, params=None):
        super().contribute_to_class(
            factory_class,
            meta=meta,
            base_meta=base_meta,
            base_factory=base_factory,
            params=params
        )
        self.add_base_fields()
        self.add_sub_factories()
        self.add_related_factories()
        self.add_m2m_factories()
        # Reevaluated declarations:
        for k, v in vars(self.factory).items():
            if self._is_declaration(k, v):
                self.base_declarations[k] = v
        self.pre_declarations, self.post_declarations = (
            factory.builder.parse_declarations(self.declarations))


class MIZModelFactory(factory.django.DjangoModelFactory):
    _options_class = MIZDjangoOptions
    # __memo remembers the kwargs for the model instance creation that were
    # explicitly passed in.
    __memo = []

    @classmethod
    def set_memo(cls, value):
        if cls.__memo and value and value != cls.__memo:
            # Memo already set for this factory.
            return
        if len(cls._meta.django_get_or_create) <= 1:
            # django_get_or_create contains one field or less;
            # no need to set the memo.
            return
        cls.__memo = value

    @classmethod
    def full_relations(cls, **kwargs):
        """
        Create a model instance with a related object for each possible relation.
        """
        backup = []
        for name, decl in cls._meta.pre_declarations.as_dict().items():
            if (hasattr(decl, 'required') and not decl.required
                    and name not in kwargs):
                # This declaration is not required by default and no value fo
                # it was passed in as kwarg.
                # Set it to be required so the factory will create data for it.
                backup.append(name)
                decl.required = True

        for name in cls._meta.post_declarations:
            # Add an extra item to every post_declaration unless one was
            # already passed in as kwarg.
            if (name not in kwargs
                    and not any(s.startswith(name + '__') for s in kwargs)):
                kwargs[name + '__extra'] = 1

        step = factory.builder.StepBuilder(
            cls._meta, kwargs, factory.enums.CREATE_STRATEGY
        )
        cls._meta._initialize_counter()
        created = step.build()
        for name in backup:
            cls._meta.pre_declarations[name].declaration.required = False
        return created

    @classmethod
    def _generate(cls, strategy, params):
        """
        Generate the object.

        Arguments:
            params (dict): attributes to use for generating the object
            strategy: the strategy to use
        """
        if params and len(cls._meta.django_get_or_create) > 1:
            # This factory has been called with explicit parameters for some of
            # its fields. Add these fields to the memo so we can distinguish
            # passed in parameters from *generated* ones.
            cls.set_memo(list(params.keys()))
        return super()._generate(strategy, params)

    @classmethod
    def _get_or_create(cls, model_class, **kwargs):
        """Create an instance of the model through manager.get_or_create."""
        manager = cls._get_manager(model_class)

        assert 'defaults' not in cls._meta.django_get_or_create, (
            "'defaults' is a reserved keyword for get_or_create "
            "(in %s._meta.django_get_or_create=%r)"
            % (cls, cls._meta.django_get_or_create))

        # get_or_create queries should only be done with values explicitly
        # passed in. Including values generated by declarations in that query
        # would make it very unlikely to find the instance that was requested.
        # __memo contains the keys of the kwargs the factory was called with.
        get_or_create_fields = []
        for field in cls._meta.django_get_or_create.copy():
            if cls.__memo and field not in cls.__memo:
                # This field's value was generated by a declaration, do not
                # include it in a get_or_create query.
                continue
            get_or_create_fields.append(field)

        if not get_or_create_fields:
            # All fields that could be used to get an object from the database
            # had their values randomly generated. There is no point in even
            # looking for a matching record, so just create a new one.
            instance = manager.create(**kwargs)
        else:
            key_fields = {}
            for field in get_or_create_fields:
                if field not in kwargs:
                    continue
                key_fields[field] = kwargs.pop(field)
            # 'defaults' contains the data which get_or_create would
            # create a new instance with.
            key_fields['defaults'] = kwargs
            instance, _created = manager.get_or_create(**key_fields)
        cls.__memo = []
        # Refresh the instance's data. This can be necessary if the instance
        # was created i.a. with data of type string for a DateField.
        instance.refresh_from_db()
        return instance


# Store the factories created via modelfactory_factory
# so that sequences are shared.
_cache = {}


def modelfactory_factory(model, **kwargs):
    """Create a factory class for the given model."""
    model_name = model._meta.model_name
    # Check the cache for a factory for that model_name.
    if model_name in _cache:
        return _cache[model_name]
    # Check this module and the factory's base module for a factory
    # matching the name.
    factory_name = model_name.capitalize() + 'Factory'
    if hasattr(sys.modules[__name__], factory_name):
        return getattr(sys.modules[__name__], factory_name)
    if hasattr(sys.modules['factory.base'], factory_name):
        return getattr(sys.modules['factory.base'], factory_name)
    # Create a new factory class:
    if 'Meta' not in kwargs:
        kwargs['Meta'] = type('Options', (MIZDjangoOptions,), {'model': model})
    modelfac = type(factory_name, (MIZModelFactory, ), kwargs)
    _cache[model_name] = modelfac
    return modelfac


class AutorFactory(MIZModelFactory):
    class Meta:
        model = _models.Autor
    person = SubFactory('DBentry.factory.PersonFactory', required=True)

    @factory.lazy_attribute
    def kuerzel(obj):
        if obj.person is None:
            return 'XY'
        if obj.person.vorname:
            return obj.person.vorname[0] + obj.person.nachname[0]
        return obj.person.nachname[:2].upper()


class BandFactory(MIZModelFactory):
    class Meta:
        model = _models.Band
        django_get_or_create = ['band_name']
    band_name = factory.Faker('company')


class BundeslandFactory(MIZModelFactory):
    class Meta:
        model = _models.bundesland
        django_get_or_create = ['bland_name', 'code']
    bland_name = factory.Faker('state')
    code = factory.Faker('state_abbr')


class GenreFactory(MIZModelFactory):
    class Meta:
        model = _models.Genre
        django_get_or_create = ['genre']


class LandFactory(MIZModelFactory):
    class Meta:
        model = _models.land
        django_get_or_create = ['land_name', 'code']
    land_name = UniqueFaker('country')
    # land.code has unique=True and max_length of 4.
    # If we were to use a UniqueFaker that max_length might be exceeded
    # depending on the sequence counter (even with a faker that returns very
    # short strings such as 'country_code').
    # So just use the last four chars from the land_name:
    code = factory.LazyAttribute(lambda o: o.land_name[-4:])


class MagazinFactory(MIZModelFactory):
    class Meta:
        model = _models.magazin
        django_get_or_create = ['magazin_name']
    magazin_name = factory.Sequence(lambda n: 'TestMagazin' + str(n))
    issn = ISSNFaker()


class MonatFactory(MIZModelFactory):
    class Meta:
        model = _models.monat
        django_get_or_create = ['monat', 'abk', 'ordinal']
    monat = factory.Faker('month_name')
    abk = factory.LazyAttribute(lambda o: o.monat[:3])
    ordinal = factory.Sequence(lambda n: n)


class MusikerFactory(MIZModelFactory):
    class Meta:
        model = _models.Musiker
        django_get_or_create = ['kuenstler_name']
    kuenstler_name = factory.Sequence(lambda n: 'TestMusiker' + str(n))


class OrtFactory(MIZModelFactory):
    class Meta:
        model = _models.ort
    stadt = factory.Faker('city')


class PersonFactory(MIZModelFactory):
    class Meta:
        model = _models.Person
    vorname = factory.Faker('first_name')
    nachname = factory.Faker('last_name')


class SchlagwortFactory(MIZModelFactory):
    class Meta:
        model = _models.schlagwort
        django_get_or_create = ['schlagwort']


def make(model, **kwargs):
    return modelfactory_factory(model)(**kwargs)


def batch(model, num, **kwargs):
    for _i in range(num):
        yield modelfactory_factory(model)(**kwargs)
