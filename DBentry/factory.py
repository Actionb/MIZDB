import random
import itertools

import factory

from DBentry.utils import is_iterable
from DBentry.base.models import get_model_relations, get_model_fields

#TODO: put logging back in for RelatedFactory
# logger = factory.declarations.logger
        
class RelatedFactory(factory.RelatedFactory):
    """
    A related factory that can handle iterables passed in.
    
    Attributes:
        accessor_name (str): the name of the model's attribute that refers to the relation's accessor (???)
        extra (int): the number of extra objects to create in addition to the objects that result from the passed in kwargs
    
    
    class BuchFactory():
        autor = RelatedFactory(AutorFactory,'buch')
    
    Example: BuchFactory(autor__name=['Alice','Bob','Charlie'], autor__kuerzel=['Al','Bo'],ort = 'Dortmund')
        results in three calls to AutorFactory
            with context.extra = {'name':['Alice','Bob','Charlie'], 'kuerzel':['Al','Bo'], 'ort':'Dortmund'}:
        => AutorFactory(name='Alice',kuerzel='Bob', ort = 'Dortmund')
        => AutorFactory(name='Bob',kuerzel='Bo', ort = 'Dortmund')
        => AutorFactory(name='Charlie',ort = 'Dortmund')
    
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
            if any(is_iterable(v) for v in context.extra.values()):
                iterables = {k:v for k, v in context.extra.items() if is_iterable(v)} # => {'name':['Alice','Bob','Charlie'], 'kuerzel':['Al','Bo']}
                singles = {k:v for k, v in context.extra.items() if k not in iterables} # => {'beschreibung' : 'Test'}
                for value in itertools.zip_longest(*iterables.values()): # => [('Alice','Al'), ('Bob','Bo'),('Charlie',None)]
                    #TODO: deepcopy necessary?
                    kwargs = dict(self.defaults)
                    kwargs.update(singles)
                    kwargs.update({k:v for k, v in zip(iterables.keys(), value) if v is not None})
                    if self.name: kwargs[self.name] = instance
                    passed_kwargs.append(kwargs)
            else:
                kwargs = dict(self.defaults)
                kwargs.update(context.extra)
                if self.name: kwargs[self.name] = instance
                passed_kwargs.append(kwargs)
                
            for kwargs in passed_kwargs:
                related_objects.append(step.recurse(factory, kwargs))
            while extra > 0:
                related_objects.append(step.recurse(factory, {}))
                extra -=1 
                
        return related_objects
                
class M2MFactory(RelatedFactory):
    """
    Attributes:
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
        
        m2m_table = related_manager.through
        if isinstance(instance, related_manager.through._meta.get_field(related_manager.source_field_name).related_model):
            source = related_manager.source_field_name
            target = related_manager.target_field_name
        else:
            source = related_manager.target_field_name
            target = related_manager.source_field_name
        
        self.name = source
        
        for related_object in super().call(instance, step, context):
            related_manager.through.objects.create(**{source:instance, target:related_object})

class MIZDjangoOptions(factory.django.DjangoOptions):

    def _get_factory_name_for_model(self, model):
        class_name = model.__name__.replace('m2m_', '').replace('_', ' ').title().replace(' ', '')
        return self.factory.__module__ + '.' + class_name + 'Factory'
        
    def add_base_fields(self):
        pass
        
    def add_m2m_factories(self):
        for rel in get_model_relations(self.model):
            if not rel.many_to_many:
                continue
            if self.model == rel.field.model:
                # the ManyToManyField is declared on model
                factory_name = self._get_factory_name_for_model(rel.related_model)
                descriptor_name = rel.field.name
            else:
                # the ManyToManyField is declared on the related_model
                factory_name = self._get_factory_name_for_model(rel.model)
                descriptor_name = rel.get_accessor_name()
            if not hasattr(self.factory, descriptor_name):
                setattr(self.factory, descriptor_name, M2MFactory(factory_name, descriptor_name = descriptor_name))
        
    def add_related_factories(self):
        for rel in get_model_relations(self.model, forward = False):
            if rel.many_to_many: 
                continue
            factory_name = self._get_factory_name_for_model(rel.model)
            accessor_name = rel.get_accessor_name()
            if not hasattr(self.factory, accessor_name):
                setattr(self.factory, accessor_name, RelatedFactory(
                    factory_name, factory_related_name = rel.field.name, accessor_name = accessor_name
                ))
        
    def add_sub_factories(self):
        for field in get_model_fields(self.model, base = False, foreign = True, m2m = False):
            if not hasattr(self.factory, field.name):
                factory_name = self._get_factory_name_for_model(field.related_model)
                setattr(self.factory, field.name, factory.SubFactory(factory_name))
    
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
    
def modelfactory_factory(model, **kwargs):
    if 'Meta' not in kwargs:
        kwargs['Meta'] = type('Options', (MIZDjangoOptions,), {'model':model})
    model_name = model.split('.')[-1] if isinstance(model, str) else model._meta.model_name
    return type(model_name.capitalize() + 'Factory', (MIZModelFactory, ), kwargs)
