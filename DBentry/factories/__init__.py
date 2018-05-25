import factory
import random

def add_m2m(instance, create, extracted, descriptor_name = None, **kwargs):
    if not create:
        return
    if extracted and descriptor_name:
        for obj in extracted:
            getattr(instance, descriptor_name).add(obj)
            
class M2MDeclaration(factory.PostGeneration):
    
    def __init__(self, descriptor_name):
        self.descriptor_name = descriptor_name
        super().__init__(add_m2m)
        
    def call(self, instance, step, context):
        context.extra['descriptor_name'] = self.descriptor_name
        return super().call(instance, step, context)
        
        
        
    
def _write_factories(module_name, required_only = True):
    from django.apps import apps
    from DBentry.base.models import get_required_fields, get_model_fields, get_relation_info_to
    
    def get_model_list(module_name):
        models = [m for m in apps.get_models('DBentry') if m.__module__ == module_name and not m._meta.auto_created]
        models = sorted(
            models, 
            key = lambda m: m._meta.model_name
        )
        return models
        
    def fac_class_name(model):
        class_name = model.__name__.replace('m2m_', '').replace('_', ' ').title().replace(' ', '')
        return class_name + 'Factory'
        
    def get_provider(field):
        if field.choices:
            return "factory.Iterator({})".format(str([tpl[0] for tpl in field.choices]))
        if field.unique:
            if field.get_internal_type() in ('CharField', 'TextField'):
                return "factory.Sequence(lambda n: 'Test{}-' + str(n))".format(field.verbose_name)
            return "factory.Sequence(lambda n: n)"
        defaults = {
            'CharField' : "factory.Faker('word')", 
            'TextField' : "factory.Faker('sentence')", 
            'NullBooleanField' : 'False', 
            'BooleanField' : 'False', 
            'PositiveSmallIntegerField' : "random.randrange(32766)", 
            'DateField' : "factory.Faker('date')",  
            'SmallIntegerField' :  "random.randrange(32766)", 
            'BigIntegerField' :  "random.randrange(32766)", 
            'DateTimeField' : '', 
            'IntegerField' :  "random.randrange(32766)", 
            'TimeField' : "factory.Faker('time')", 
            
        }
        return defaults.get(field.get_internal_type(), '')
        
    import os
    file_name = module_name.split('.')[-1] + '.py'
    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    abs_file_path = os.path.join(script_dir, file_name)
    
    tab = ' '*4
    with open(abs_file_path,'w') as f: 
    
#        f.write('import factory\nimport random\n\n')
#        f.write('from functools import partial\n\n')
        f.write('from . import *\n')
        f.write('from {} import *\n'.format(module_name))
        f.write('\n')
        
        for m in get_model_list(module_name):
            f.write('class {}(factory.django.DjangoModelFactory):\n'.format(fac_class_name(m)))
            f.write(tab+'class Meta:\n')
            f.write(tab*2+'model = {}\n'.format(m.__name__))
            
            required_fields = get_required_fields(m)
            written = False
            
            for fld in get_model_fields(m, base = True, foreign = False, m2m = False):
                if required_only and fld not in required_fields:
                    continue
                if fld.name.startswith('_'):
                    continue
                provider = get_provider(fld)
                if not provider: f.write('#')
                f.write(tab+"{} = {}".format(fld.name, provider))
                if not required_only and fld in required_fields:
                    f.write(' #REQUIRED')
                f.write('\n')
                written = True
            if written:
                f.write('\n')
                written = False
            
            for fld in get_model_fields(m, base = False, foreign = True, m2m = False):
                if required_only and fld not in required_fields:
                    continue
                #DBentry.factories.models.
                f.write(tab+"{} = factory.SubFactory('{}')".format(fld.name, 'DBentry.factories.models.'+fac_class_name(fld.related_model)))
                if not required_only and fld in required_fields:
                    f.write(' #REQUIRED')
                f.write('\n')
                written = True
            if written:
                f.write('\n')
                written = False
            
            for fld in get_model_fields(m, base = False, foreign = False, m2m = True):
                if required_only and fld not in required_fields:
                    continue
                if fld.remote_field.through._meta.auto_created:
                    f.write(tab+"{a} = M2MDeclaration('{a}')".format(a=fld.name))
                else:
                    f.write(
                        tab+"{} = factory.RelatedFactory('{}','{}')".format(
                            fld.name, 
                            'DBentry.factories.m2m.' + fac_class_name(fld.remote_field.through), 
                            get_relation_info_to(m,fld.remote_field)[-1].name, # The name of field on the m2m table pointing to model
                        )
                    )
                f.write('\n')   
                written = True
            if written:
                f.write('\n')
                written = False

            
def _create_factories(required_only = True):
    _write_factories('DBentry.models', required_only)
    _write_factories('DBentry.m2m', required_only)
