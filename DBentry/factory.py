import itertools

import factory

from stdnum import issn

from DBentry.utils import is_iterable, get_model_relations, get_model_fields
from DBentry.models import *

#TODO: put logging back in for RelatedFactory
# logger = factory.declarations.logger

class RuntimeFactoryMixin(object):
    """
    A mixin that can create a related factory on the fly.
    
    Accepts one additional keyword argument:
        - related_model: the model class for the related factory
    
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
                # The related factory does not exist yet
                if self.related_model is None:
                    raise AttributeError('Missing related factory for {}'.format(self.name)) # TODO: more useful error message
                self._factory =  modelfactory_factory(self.related_model)
        return self._factory
        
    def get_factory(self):
        return self.factory
    
class UniqueFaker(factory.Sequence):
    """
    A faker that returns unique values.
    
    Parameters:
        - faker (str or a factory.Faker instance): the faker or a faker provider to use
        - function: the sequence callable that returns the suffix that makes the value unique; defaults to lambda n: n
    
    Only works for strings.
    """
    
    def __init__(self, faker, function = None, **kwargs):
        if function is None:
            function = lambda n: n
        super().__init__(function, **kwargs)
        self.faker = faker
        if isinstance(faker, str):
            # a provider name was passed in
            self.faker = factory.Faker(faker)
        
    def evaluate(self, instance, step, extra):
        n = super().evaluate(instance, step, extra)
        return self.faker.generate(extra) + str(n)
        
class ISSNFaker(factory.Faker):
    
    def __init__(self, provider = 'ean', **kwargs):
        super().__init__(provider, **kwargs)
        
    def generate(self, extra_kwargs):
        ean = super().generate(extra_kwargs)
        return ean[3:-3] + issn.calc_check_digit(ean[3:-3])    

class SubFactory(RuntimeFactoryMixin, factory.SubFactory):
    
    def __init__(self, factory, required = False, **kwargs):
        self.required = required
        super().__init__(factory, **kwargs)
        
    def evaluate(self, instance, step, extra):
        # Do not generate an object unless required or parameters are declared in extra.
        if not self.required and not extra:
            return
        # evaluate() is called while resolving the pre-declarations of a factory.
        # Extra contains explicitly passed in parameters - the factory needs to know these when 
        # deciding on what fields to query for in get_or_create.
        self.factory.set_memo(list(extra.keys()))
        return super().evaluate(instance, step, extra)
        
class SelfFactory(SubFactory):
    
    def evaluate(self, instance, step, extra):
        # extra may define the recursion depth: extra = {field__field__field=None}
        # If extra is empty and the model field is required, the recursion should happen exactly once.
        if self.required and not extra:
            # recurse once by adding 'itself:None' to extra
            self_name = ''
            for k, v in self.factory._meta.pre_declarations.as_dict().items():
                if v == self:
                    self_name = k
                    break
            if not self_name:
                # do not recurse at all, if the SelfFactory cannot 'find itself'
                return
            extra = {self_name:None}
        return super().evaluate(instance, step, extra)
        
class RelatedFactory(RuntimeFactoryMixin, factory.RelatedFactory):
    """
    A related factory that can handle iterables passed in.
    
    Accepts two additional keyword arguments:
        - accessor_name (str): the name of the instance's attribute that refers to the relation's descriptor 
        - extra (int): the number of extra objects to create in addition to the objects that result from the passed in kwargs
    
    Example: 
        
        class BuchFactory():
            autor = RelatedFactory(AutorFactory,'buch')
        
        
        BuchFactory(autor__name=['Alice','Bob','Charlie'], autor__kuerzel=['Al','Bo'], autor__beschreibung = 'Test')
            results in three calls to AutorFactory
                with context.extra = {'name':['Alice','Bob','Charlie'], 'kuerzel':['Al','Bo'], 'beschreibung':'Test'}:
            => AutorFactory(name = 'Alice',   kuerzel = 'Al', beschreibung = 'Test')
            => AutorFactory(name = 'Bob',     kuerzel = 'Bo', beschreibung = 'Test')
            => AutorFactory(name = 'Charlie', beschreibung = 'Test')
    
    """
    
    def __init__(self, factory, factory_related_name='', accessor_name = None, extra = 0, **defaults):
        self.accessor_name = accessor_name
        self.extra = extra
        super().__init__(factory, factory_related_name, **defaults)
    
    def call(self, instance, step, context):
        factory = self.get_factory()
        related_objects = []
        
        if context.value:
            # context.value contains the related_object(s) that should be added to instance
            if isinstance(context.value, (list, tuple)):
                related_objects = list(context.value) # force tuples into lists
            else:
                related_objects = [context.value]
                
            if self.accessor_name and hasattr(instance, self.accessor_name):
                getattr(instance, self.accessor_name).add(*related_objects)
                
        if context.extra or self.extra:
            # Example: context.extra = {'name':['Alice','Bob','Charlie'], 'kuerzel':['Al','Bo'],'beschreibung':'Test'}
            extra = self.extra
            if 'extra' in context.extra:
                extra = context.extra.pop('extra')
                
            passed_kwargs = []
            default_kwargs = dict(self.defaults)
            if self.name: 
                default_kwargs[self.name] = instance
            
            if context.extra:
                if any(is_iterable(v) for v in context.extra.values()):
                    iterables = {k:v for k, v in context.extra.items() if is_iterable(v)} # => {'name':['Alice','Bob','Charlie'], 'kuerzel':['Al','Bo']}
                    singles = {k:v for k, v in context.extra.items() if k not in iterables} # => {'beschreibung' : 'Test'}
                    for value in itertools.zip_longest(*iterables.values()): # => [('Alice','Al'), ('Bob','Bo'),('Charlie',None)]
                        kwargs = default_kwargs.copy()
                        kwargs.update(singles)
                        kwargs.update({k:v for k, v in zip(iterables.keys(), value) if v is not None})
                        passed_kwargs.append(kwargs)
                else:
                    kwargs = default_kwargs.copy()
                    kwargs.update(context.extra)
                    passed_kwargs.append(kwargs)
                    
            while extra > 0:
                passed_kwargs.append(default_kwargs)
                extra -=1 
                
            for kwargs in passed_kwargs:
                related_objects.append(step.recurse(factory, kwargs))
                
        return related_objects
                
class M2MFactory(RelatedFactory):
    """
    A factory that implements a m2m relation with the added benefits of RelatedFactory.
    
    Parameters:
        descriptor_name (str): the name of the instance's attribute that refers to the relation's descriptor 
    
    """
    
    def __init__(self, factory,  descriptor_name = None, **defaults): 
        self.descriptor_name = descriptor_name
        if 'accessor_name' in defaults:
            # Having the attribute accessor_name upon calling super().call() will make the RelatedFactory try to invoke .add()
            # which is not allowed for intermediary tables that were not auto_created.
            # 'accessor_name' should not show up in **defaults as it makes little sense, but just to be sure this does not happen:
            del defaults['accessor_name']
        super().__init__(factory, **defaults)
        
    def call(self, instance, step, context):
        related_manager = getattr(instance, self.descriptor_name)
        
        if isinstance(instance, related_manager.through._meta.get_field(related_manager.source_field_name).related_model):
            source = related_manager.source_field_name
            target = related_manager.target_field_name
        else:
            source = related_manager.target_field_name
            target = related_manager.source_field_name
        
        #self.name = source
        
        for related_object in super().call(instance, step, context):
            related_manager.through.objects.create(**{source:instance, target:related_object})

class MIZDjangoOptions(factory.django.DjangoOptions):

    def _get_factory_name_for_model(self, model):
        class_name = model.__name__.replace('m2m_', '').replace('_', ' ').title().replace(' ', '')
        return self.factory.__module__ + '.' + class_name + 'Factory'
    
    @staticmethod
    def _get_decl_for_model_field(field):
        # For a given model field, return an appropriate faker declaration
        internal_type = field.get_internal_type()
        if internal_type in ('CharField', 'TextField'):
            if field.unique:
                declaration = UniqueFaker('word')
            else:
                declaration = factory.Faker('word')
        elif internal_type in ('IntegerField', 'PositiveSmallIntegerField', 'SmallIntegerField', 'BigIntegerField', 'DurationField'):
            if field.unique:
                declaration = factory.Sequence(lambda n: n)
            else:
                declaration = factory.Faker('pyint')
        elif internal_type in ('BooleanField', 'NullBooleanField'):
            declaration = factory.Faker('pybool')
        elif internal_type in ('DateField', 'DateTimeField', 'TimeField'):
            provider = ''
            for i, c in enumerate(internal_type.replace('Field', '')):
                if i and c.isupper():
                    provider += '_'
                provider += c.lower()
            declaration = factory.Faker(provider)
        return declaration
        
        
    def add_base_fields(self):
        #TODO: account for unique == True // unique_together
        for field in get_model_fields(self.model, foreign = False, m2m = False):
            if hasattr(self.factory, field.name) or field.has_default() or field.blank:
                continue
            setattr(self.factory, field.name, self._get_decl_for_model_field(field))
        
    def add_m2m_factories(self):
        for rel in get_model_relations(self.model):
            if not rel.many_to_many:
                continue
            if self.model == rel.field.model:
                # the ManyToManyField is declared on model
                related_model = rel.field.related_model
                descriptor_name = rel.field.name
                declaration_name = rel.field.name
            else:
                # the ManyToManyField is declared on the related_model, working on a 'reverse' m2m relation
                related_model = rel.field.model
                descriptor_name = rel.get_accessor_name()
                declaration_name = rel.name
            factory_name = self._get_factory_name_for_model(related_model)
            if not hasattr(self.factory, declaration_name):
                setattr(self.factory, declaration_name, M2MFactory(factory_name, descriptor_name = descriptor_name, related_model = related_model))
        
    def add_related_factories(self):
        for rel in get_model_relations(self.model, forward = False):
            if rel.many_to_many: 
                continue
            factory_name = self._get_factory_name_for_model(rel.related_model) # these are all reverse relations, meaning rel.model == self.model
            accessor_name = rel.get_accessor_name()
            if not hasattr(self.factory, rel.name):
                setattr(self.factory, rel.name, RelatedFactory(
                    factory_name, factory_related_name = rel.field.name, accessor_name = accessor_name, related_model = rel.related_model
                ))
        
    def add_sub_factories(self):
        #TODO: account for unique == True // unique_together
        for field in get_model_fields(self.model, base = False, foreign = True, m2m = False):
            if not hasattr(self.factory, field.name):
                factory_name = self._get_factory_name_for_model(field.related_model)
                if field.related_model == self.model:
                    setattr(self.factory, field.name, SelfFactory(self.factory, required = not field.null))
                else:
                    setattr(self.factory, field.name, SubFactory(factory_name, related_model = field.related_model, required = not field.null))
    
    def contribute_to_class(self, factory_class, meta=None, base_meta=None, base_factory=None, params=None):
        super().contribute_to_class(factory_class, meta=meta, base_meta=base_meta, base_factory=base_factory, params=params)
        
        self.add_base_fields()
        self.add_sub_factories()
        self.add_related_factories()
        self.add_m2m_factories()
        
        # Reevaluated declarations
        for k, v in vars(self.factory).items():
            if self._is_declaration(k, v):
                self.base_declarations[k] = v
                
        self.pre_declarations, self.post_declarations = factory.builder.parse_declarations(self.declarations)

class MIZModelFactory(factory.django.DjangoModelFactory):
    _options_class = MIZDjangoOptions
    
    __memo = [] # remembers the kwargs for the model instance creation that were explicitly passed in
    
    @classmethod
    def set_memo(cls, value):
        if cls.__memo and value and value!= cls.__memo:
            # Memo already set for this factory
            return
        if len(cls._meta.django_get_or_create)<=1:
            # Ignoring setting of Memo: django_get_or_create contains one field or less
            return
        cls.__memo = value
    
    @classmethod
    def full(cls, **kwargs):
        backup = []
        for name, decl in cls._meta.pre_declarations.as_dict().items():
            if hasattr(decl, 'required') and not decl.required and name not in kwargs:
                backup.append(name)
                decl.required = True
                
        for name, decl in cls._meta.post_declarations.as_dict().items():
            if name not in kwargs and not any(s.startswith(name + '__') for s in kwargs.keys()):
                kwargs[name + '__extra'] = 1
        
        step = factory.builder.StepBuilder(cls._meta, kwargs, factory.enums.CREATE_STRATEGY)
        created = step.build()
        
        for name in backup:
            cls._meta.pre_declarations[name].declaration.required = False
        
        return created

    @classmethod
    def _generate(cls, strategy, params):
        """generate the object.

        Args:
            params (dict): attributes to use for generating the object
            strategy: the strategy to use
        """
        if params and len(cls._meta.django_get_or_create)>1:
            # This factory has been called with explicit parameters for some of its fields.
            # Add these fields to the memo so we can distinguish passed in parameters from *generated* ones.
            cls.set_memo(list(params.keys()))
        return super()._generate(strategy, params)

    @classmethod
    def _get_or_create(cls, model_class, *args, **kwargs):
        """Create an instance of the model through objects.get_or_create."""
        manager = cls._get_manager(model_class)

        assert 'defaults' not in cls._meta.django_get_or_create, (
            "'defaults' is a reserved keyword for get_or_create "
            "(in %s._meta.django_get_or_create=%r)"
            % (cls, cls._meta.django_get_or_create))

        # In case of a multi-field get or create setup, any fields in get_or_create_fields that 
        # is not in memo had their values *generated* and not passed in.
        # This can lead to not finding the model instance that the explicitly passed in kwargs
        # refer to.
        get_or_create_fields = []
        for field in cls._meta.django_get_or_create.copy():
            if cls.__memo and field not in cls.__memo:
                # This field's value was generated by a declaration, do not include it in a get_or_create query.
                continue
            get_or_create_fields.append(field)
            
        if not get_or_create_fields:
            instance =  manager.create(*args, **kwargs)
        else:
            key_fields = {}
            for field in get_or_create_fields:
                if field not in kwargs:
                    continue
                key_fields[field] = kwargs.pop(field)
            key_fields['defaults'] = kwargs
            instance, _created = manager.get_or_create(*args, **key_fields)
        cls.__memo = []
        #FIXME: the returned instance has not been refreshed_from_db 
        # i.e.: ausgabe instances can have a str for their e_datum attribute
        return instance
            

# Stores the factories created via modelfactory_factory so that sequences are shared
_cache = {}
    
def modelfactory_factory(model, **kwargs):
    #TODO: have a look at factory.helper.make_factory
    if 'Meta' not in kwargs:
        kwargs['Meta'] = type('Options', (MIZDjangoOptions,), {'model':model})
    model_name = model.split('.')[-1] if isinstance(model, str) else model._meta.model_name
    
    if model_name in _cache:
        return _cache[model_name]
    
    factory_name = model_name.capitalize() + 'Factory'
    import sys
    if hasattr(sys.modules[__name__], factory_name):
        return getattr(sys.modules[__name__], factory_name)
    if hasattr(sys.modules['factory.base'], factory_name):
        return getattr(sys.modules['factory.base'], factory_name)
    
    modelfac = type(factory_name, (MIZModelFactory, ), kwargs)
    _cache[model_name] = modelfac
    return modelfac

class AutorFactory(MIZModelFactory):
    class Meta:
        model = autor
    person = SubFactory('DBentry.factory.PersonFactory', required = True)
    
    @factory.lazy_attribute
    def kuerzel(object):
        if object.person is None:
            return 'XY'
        if object.person.vorname:
            return object.person.vorname[0] + object.person.nachname[0]
        return object.person.nachname[:2].upper()

class BandFactory(MIZModelFactory):
    class Meta:
        model = band
        django_get_or_create = ['band_name']
    band_name = factory.Faker('company')
    
class BundeslandFactory(MIZModelFactory):
    class Meta:
        model = bundesland
        django_get_or_create = ['bland_name', 'code']
    bland_name = factory.Faker('state')
    code = factory.Faker('state_abbr')
    
class GenreFactory(MIZModelFactory):
    class Meta:
        model = genre
        django_get_or_create = ['genre']
    
class LandFactory(MIZModelFactory):
    class Meta:
        model = land
        django_get_or_create = ['land_name', 'code']
    land_name = UniqueFaker('country')
    code = UniqueFaker('country_code')

class MagazinFactory(MIZModelFactory):
    class Meta:
        model = magazin
        django_get_or_create = ['magazin_name']
    magazin_name = factory.Sequence(lambda n: 'TestMagazin' + str(n))
    issn = ISSNFaker()
    
class MonatFactory(MIZModelFactory):
    class Meta:
        model = monat
        django_get_or_create = ['monat', 'abk', 'ordinal']
    monat = factory.Faker('month_name')
    abk = factory.LazyAttribute(lambda o: o.monat[:3])
    ordinal = factory.Sequence(lambda n: n)   
    
class MusikerFactory(MIZModelFactory):
    class Meta:
        model = musiker
        django_get_or_create = ['kuenstler_name']
    kuenstler_name = factory.Sequence(lambda n: 'TestMusiker' + str(n))
    
class OrtFactory(MIZModelFactory):
    class Meta:
        model = ort
    stadt = factory.Faker('city')
    
class PersonFactory(MIZModelFactory):
    class Meta:
        model = person
    vorname = factory.Faker('first_name')
    nachname = factory.Faker('last_name')
    
class SchlagwortFactory(MIZModelFactory):
    class Meta:
        model = schlagwort
        django_get_or_create = ['schlagwort']
    
class SpracheFactory(MIZModelFactory):
    class Meta:
        model = sprache
    abk = factory.Faker('language_code')
    
def make(model, **kwargs):
    return modelfactory_factory(model)(**kwargs)
    
def batch(model, num, **kwargs):
    for i in range(num):
        yield modelfactory_factory(model)(**kwargs)
        
