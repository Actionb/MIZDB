# WARNING: unique together options are not really supported. Use with caution.
import itertools
import sys
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Type, Union

import factory
from django.db.models import Field, Model
from factory import builder, declarations
from stdnum import issn

import dbentry.models as _models
from dbentry.fields import PartialDateField
from dbentry.utils import get_model_fields, get_model_relations, is_iterable


class UniqueFaker(factory.Sequence):
    """
    A faker that returns unique values by using sequences.
    Only works for strings.
    """

    def __init__(
            self,
            faker: Union[str, factory.Faker],
            function: Optional[Callable] = None,
            **faker_kwargs: Any
    ) -> None:
        """
        Initialize the faker.

        Args:
            faker (str or a factory.Faker instance): the faker or the name of a
              faker provider to use
            function (callable): the factory sequence callable that returns the
              suffix that makes the value unique; defaults to lambda n: n
            faker_kwargs: additional arguments for the Faker initialization
        """
        if function is None:
            def default_callable(n):
                return n

            function = default_callable
        super().__init__(function)
        if isinstance(faker, str):
            # A provider name was passed in.
            self.faker = factory.Faker(faker, **faker_kwargs)
        else:
            self.faker = faker

    def evaluate(
            self,
            instance: builder.Resolver,
            step: builder.BuildStep,
            extra: dict
    ) -> str:
        n = super().evaluate(instance, step, extra)
        if 'locale' not in extra:
            # faker.evaluate will attempt extra.pop('locale'), but, by default,
            # Sequences do not use a locale and none is provided in extra.
            extra['locale'] = None
        return self.faker.evaluate(instance, step, extra) + str(n)


class ISSNFaker(factory.Faker):
    """A faker that provides valid ISSN."""

    def __init__(self, provider: str = 'ean', **kwargs: Any) -> None:
        super().__init__(provider, **kwargs)

    def evaluate(self, instance, step, extra):
        ean = super().evaluate(instance, step, extra)
        return ean[3:-3] + issn.calc_check_digit(ean[3:-3])


class RuntimeFactoryMixin(object):
    """
    A mixin that can create a missing related factory during runtime.

    Accepts the additional keyword argument ``related_model`` which is the
    model class for the factory class that would be created if it was found
    missing.
    This argument can be omitted if the factory already exists, i.e. if
    factory.declarations._FactoryWrapper can resolve the factory arg into a
    factory class.
    """

    def __init__(
            self,
            *args: Any,
            related_model: Optional[Type[Model]] = None,
            **kwargs: Any
    ) -> None:
        self.related_model = related_model
        self._factory: Optional[Type['MIZModelFactory']] = None
        super().__init__(*args, **kwargs)  # type: ignore[call-arg]

    @property
    def factory(self) -> Type['MIZModelFactory']:
        """Create a factory for the related model class."""
        if self._factory is None:
            try:
                # Let the _FactoryWrapper try and resolve the factory.
                # If the factory was 'declared' as a fully qualified name,
                # the wrapper will attempt to first import the module, then
                # get the named factory from that module using getattr
                # (see factory.utils.import_object). An AttributeError will
                # then be raised, if a factory with that name has not (yet)
                # been declared in that module.
                # noinspection PyUnresolvedReferences
                self._factory = super().get_factory()  # type: ignore[misc]
            except AttributeError:
                # The factory does not exist yet.
                if self.related_model is None:
                    # noinspection PyUnresolvedReferences
                    raise AttributeError(
                        'Cannot create missing factory for {}: '
                        'no related model class provided. '.format(
                            self.name  # type: ignore[attr-defined]
                        )
                    )
                self._factory = modelfactory_factory(self.related_model)
        return self._factory

    def get_factory(self) -> Type['MIZModelFactory']:
        return self.factory


class SubFactory(RuntimeFactoryMixin, factory.SubFactory):
    """
    A SubFactory that does not automatically create objects unless required.
    """

    def __init__(self, *args: Any, required: bool = False, **kwargs: Any) -> None:
        """
        Initialize the SubFactory.

        Args:
            required (bool): whether this SubFactory MUST create an object
              (usually: the field that this SubFactory represents is required
              i.e. not nullable)
        """
        self.required = required
        super().__init__(*args, **kwargs)

    def evaluate(
            self,
            instance: builder.Resolver,
            step: builder.BuildStep,
            extra: dict
    ) -> Optional[Model]:
        # Do not generate an object unless required or parameters are declared
        # in extra.
        if not self.required and not extra:
            return None
        # evaluate() is called while resolving the pre-declarations of a
        # factory. 'extra' contains explicitly passed in parameters, and the
        # factory needs to know these when deciding on what fields to query
        # for in get_or_create. Store the parameters for later:
        self.factory.set_memo(tuple(extra.keys()))
        return super().evaluate(instance, step, extra)


class SelfFactory(SubFactory):
    """
    A SubFactory used for recursive relations.

    If this SubFactory was declared for field ``foo``, then a call to the
    parent factory with ``foo__foo__foo=None`` would mean 2 recursions.
    (the final foo, i.e. the foo of foo__foo, is meant to be None)
    """

    def evaluate(
            self,
            instance: builder.Resolver,
            step: builder.BuildStep,
            extra: dict
    ) -> Optional[Model]:
        # 'extra' may define the recursion depth:
        # extra = {field__field__field=None}
        # If 'extra' is empty and the declaration is required, the recursion
        # should happen exactly once.
        if self.required and not extra:
            # Find the attribute name that refers to this factory declaration:
            self_name = ''
            for k, v in self.factory._meta.pre_declarations.as_dict().items():
                if v == self:
                    self_name = k
                    break
            if not self_name:
                # The SelfFactory could not 'find itself' in the factory's
                # declarations: do not recurse at all.
                return None
            # Recurse once by adding 'itself: None' to extra.
            extra = {self_name: None}
        return super().evaluate(instance, step, extra)


class RelatedFactory(RuntimeFactoryMixin, factory.RelatedFactory):
    """
    A related factory that can handle iterables passed in.

    Additional attributes:
        ``accessor_name`` (str): the name of the instance's attribute that
          refers to the accessor for related objects (the related manager)
        ``extra`` (int): the number of extra objects to create in addition to
          the objects that result from the passed in parameters
    ----

    For example, take this BuchFactory:
        class BuchFactory():
            autor = RelatedFactory(AutorFactory,'buch')

    A call such as:
        BuchFactory(
            autor__name=['Alice','Bob','Charlie'],
            autor__kuerzel=['Al','Bo'],
            autor__beschreibung = 'Test'
        )

    means that the context.extra to the AutorFactory.call() will be:
        {
            'name':['Alice','Bob','Charlie'],
            'kuerzel':['Al','Bo'],
            'beschreibung':'Test'
        }

    which results in three calls to AutorFactory:
        AutorFactory(name='Alice', kuerzel='Al', beschreibung='Test')
        AutorFactory(name='Bob', kuerzel='Bo', beschreibung='Test')
        AutorFactory(name='Charlie', beschreibung='Test')
    """

    def __init__(self, *args: Any, accessor_name: str = '', extra: int = 0, **kwargs: Any) -> None:
        self.accessor_name = accessor_name
        self.extra = extra
        super().__init__(*args, **kwargs)

    def call(
            self,
            instance: Model,
            step: builder.BuildStep,
            context: declarations.PostGenerationContext
    ) -> List[Model]:
        """Return the related objects for model instance ``instance``."""
        factory_class = self.get_factory()
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
            # From the class docstring example:
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
                    # Create keyword arguments for all the related instances
                    # expected to be created from the iterables, supplementing
                    # missing values with None (zip_longest).
                    # e.g: [('Alice','Al'), ('Bob','Bo'),('Charlie',None)]
                    for value in itertools.zip_longest(*iterables.values()):
                        kwargs = default_kwargs.copy()
                        kwargs.update(singles)
                        kwargs.update(
                            {
                                k: v for k, v in zip(iterables.keys(), value)
                                if v is not None
                            }
                        )
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
                related_objects.append(step.recurse(factory_class, kwargs))
        return related_objects


class M2MFactory(RelatedFactory):
    """
    A RelatedFactory that handles a many-to-many relation.

    Additional attribute:
        ``descriptor_name`` (str): the name of the instance's attribute that
          refers to the relation's descriptor (for the related manger)
    """

    def __init__(self, *args: Any, descriptor_name: str, **kwargs: Any) -> None:
        self.descriptor_name = descriptor_name
        super().__init__(*args, **kwargs)

    def call(  # type: ignore[override]
            self,
            instance: Model,
            step: builder.BuildStep,
            context: declarations.PostGenerationContext
    ) -> None:
        """Create the related objects and add references to the m2m table."""
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

    def _get_factory_name_for_model(self, model: Type[Model]) -> str:
        """Return the probable factory name for a given model class."""
        class_name = model.__name__.replace('m2m_', '').replace('_', ' ').title().replace(' ', '')
        return self.factory.__module__ + '.' + class_name + 'Factory'

    @staticmethod
    def _get_decl_for_model_field(field: Field) -> Optional[declarations.BaseDeclaration]:
        """For a given model field, return an appropriate faker declaration."""
        if isinstance(field, PartialDateField):
            return factory.Faker('date')
        internal_type = field.get_internal_type()
        declaration = None
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
        if declaration is None:
            raise Exception(
                f"Could not find a faker declaration appropriate for model field {field!r}"
            )
        return declaration

    def add_base_fields(self) -> None:
        """
        Add to this factory any field of the model that requires a value and is
        not a relation.
        """
        for field in get_model_fields(self.model, foreign=False, m2m=False):
            if hasattr(self.factory, field.name) or field.has_default() or field.blank:
                continue
            setattr(
                self.factory, field.name, self._get_decl_for_model_field(field)
            )

    def add_m2m_factories(self) -> None:
        """Add M2MFactories for every many-to-many relation of this model."""
        opts = self.model._meta
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
                if rel.field.model in opts.parents:
                    # self.model inherited the actual ManyToManyField.
                    # Use the inherited ManyToManyField's name for descriptor
                    # and declaration.
                    related_model = rel.field.related_model
                    descriptor_name = rel.field.name
                    declaration_name = rel.field.name
                elif rel.field.related_model in opts.parents:
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
                    factory=factory_name,
                    descriptor_name=descriptor_name,
                    related_model=related_model
                )
                setattr(self.factory, declaration_name, m2m_factory)

    def add_related_factories(self) -> None:
        """
        Add RelatedFactories for every many-to-one (i.e. reverse) relation of
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
                    factory=factory_name,
                    factory_related_name=rel.field.name,
                    accessor_name=accessor_name,
                    related_model=rel.related_model
                )
                setattr(self.factory, rel.name, related_factory)

    def add_sub_factories(self) -> None:
        """
        Add SubFactories for every (forward) one-to-many relation of this model.
        """
        for field in get_model_fields(self.model, base=False, foreign=True, m2m=False):
            if not hasattr(self.factory, field.name):
                factory_name = self._get_factory_name_for_model(field.related_model)
                if field.related_model == self.model:
                    _factory = SelfFactory(factory=self.factory, required=not field.null)
                else:
                    _factory = SubFactory(
                        factory=factory_name,
                        required=not field.null,
                        related_model=field.related_model
                    )
                setattr(self.factory, field.name, _factory)

    def contribute_to_class(self, *args: Any, **kwargs: Any) -> None:
        """Add the additional factories and declarations."""
        super().contribute_to_class(*args, **kwargs)
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
    """
    Factory for the models of the dbentry app.

    Uses MIZDjangoOptions as options class - which creates most of the
    declarations for the factory. Since values randomly generated by those
    declarations are of no use for a django get_or_create query
    (get() returning an instance would be pure chance), this factory will
    memorize the names of model fields for which the caller had passed in
    explicit values, and use only those fields and values in the get_or_create
    query.

    Attributes:
        __memo: a tuple of names of the model fields for which the caller had
          passed in explicit values - i.e. the instance's values on those
          fields were not (randomly) generated by declarations
    """
    _options_class = MIZDjangoOptions

    __memo: Tuple[str, ...] = ()

    @classmethod
    def set_memo(cls, fields: Sequence[str]) -> None:
        """Memorize the model field names that had declared values."""
        fields = tuple(fields)
        if cls.__memo and fields and fields != cls.__memo:
            # Memo already set for this factory.
            # NOTE: shouldn't we update the memo here?
            return
        if len(cls._meta.django_get_or_create) <= 1:
            # django_get_or_create contains one field or less;
            # no need to set the memo, as issues only arise when multiple
            # fields (of which some (or all) have randomly generated values)
            # are used in the query.
            return
        cls.__memo = fields

    @classmethod
    def full_relations(cls, **kwargs: Any) -> Model:
        """
        Create a model instance with a related object for each possible relation.
        """
        set_to_required = []
        for name, decl in cls._meta.pre_declarations.as_dict().items():
            if (hasattr(decl, 'required') and not decl.required
                    and name not in kwargs):
                # This declaration is not required by default and no value for
                # it was passed in as kwarg.
                # Set it to be required so the factory will create data for it.
                set_to_required.append(name)
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
        for name in set_to_required:
            cls._meta.pre_declarations[name].declaration.required = False
        return created

    @classmethod
    def _generate(cls, strategy: str, params: dict) -> Model:
        """
        Generate the object.

        Arguments:
            strategy (str): the strategy to use
              (i.e. 'build', 'create', 'stub'; see factory.enums)
            params (dict): attributes to use for generating the object
        """
        if params and len(cls._meta.django_get_or_create) > 1:
            # This factory has been called with explicit parameters for some of
            # its fields. Add these fields to the memo, so we can distinguish
            # passed in parameters from *generated* ones.
            cls.set_memo(tuple(params.keys()))
        return super()._generate(strategy, params)

    @classmethod
    def _get_or_create(cls, model_class: Type[Model], **kwargs: Any) -> Model:
        """Create an instance of the model through manager.get_or_create."""
        manager = cls._get_manager(model_class)

        assert 'defaults' not in cls._meta.django_get_or_create, (
                "'defaults' is a reserved keyword for get_or_create "
                "(in %s._meta.django_get_or_create=%r)"
                % (cls, cls._meta.django_get_or_create))

        # get_or_create queries should only be done with values that have been
        # passed in explicitly. Including values generated by declarations in
        # that query would make it very unlikely to find the instance that was
        # requested.
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
        cls.__memo = ()
        # Refresh the instance's data. This can be necessary if the instance
        # was created i.a. with data of type string for a DateField.
        instance.refresh_from_db()
        return instance


# Store the factories created via modelfactory_factory
# so that sequences are shared.
_cache: Dict[str, Type[MIZModelFactory]] = {}


def modelfactory_factory(model: Type[Model], **kwargs: Any) -> Type[MIZModelFactory]:
    """Create a factory class for the given model."""
    # noinspection PyUnresolvedReferences
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
    modelfac = type(factory_name, (MIZModelFactory,), kwargs)
    # noinspection PyTypeChecker
    _cache[model_name] = modelfac
    # noinspection PyTypeChecker
    return modelfac


class AutorFactory(MIZModelFactory):
    class Meta:
        model = _models.Autor

    person = SubFactory('dbentry.factory.PersonFactory', required=True)

    # noinspection PyUnresolvedReferences,PyMethodParameters
    @factory.lazy_attribute
    def kuerzel(obj):
        """Prepare a 2 character token based on the Person's name."""
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
        model = _models.Bundesland
        django_get_or_create = ['bland_name', 'code']

    bland_name = factory.Faker('state')
    code = factory.Faker('state_abbr')


class GenreFactory(MIZModelFactory):
    class Meta:
        model = _models.Genre
        django_get_or_create = ['genre']


class LandFactory(MIZModelFactory):
    class Meta:
        model = _models.Land
        django_get_or_create = ['land_name', 'code']

    land_name = UniqueFaker('country')
    # land.code has unique=True and max_length of 4.
    # If we were to use a UniqueFaker that max_length might be exceeded
    # depending on the sequence counter (even with a faker that returns very
    # short strings such as 'country_code').
    # The end of land_name includes a unique sequence element, so just use the
    # last four chars of that name:
    code = factory.LazyAttribute(lambda o: o.land_name[-4:])


class MagazinFactory(MIZModelFactory):
    class Meta:
        model = _models.Magazin
        django_get_or_create = ['magazin_name']

    magazin_name = factory.Sequence(lambda n: 'TestMagazin' + str(n))
    issn = ISSNFaker()


class MonatFactory(MIZModelFactory):
    class Meta:
        model = _models.Monat
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
        model = _models.Ort

    stadt = factory.Faker('city')


class PersonFactory(MIZModelFactory):
    class Meta:
        model = _models.Person

    vorname = factory.Faker('first_name')
    nachname = factory.Faker('last_name')


class SchlagwortFactory(MIZModelFactory):
    class Meta:
        model = _models.Schlagwort
        django_get_or_create = ['schlagwort']


def make(model: Type[Model], **kwargs: Any) -> Model:
    """
    Create a single model instance for the given model class using initial data
    from the kwargs.
    """
    return modelfactory_factory(model)(**kwargs)


def batch(model: Type[Model], num: int, **kwargs: Any) -> Iterator[Model]:
    """
    Create a number of model instance for the given model class using initial
    data from the kwargs.
    """
    for _i in range(num):
        yield modelfactory_factory(model)(**kwargs)
