#
from django.db import transaction
from .discogs import DiscogsImporter
        
class RelationImport(object):
    
    def __init__(self, relations, importer_class = DiscogsImporter, file = None, key = 'release_id', ignore_existing = True):
        mcs = {}
        models = set()
        self._save_order = []
        for relation in relations:
            parent = relation.related_model
            child = relation.model
            if parent not in mcs:
                parent_mc = ModelContainer(parent, key=key)
                models.add(parent)
                mcs[parent] = parent_mc
            else:
                parent_mc = mcs[parent]
            if child not in mcs:
                child_mc = ModelContainer(child, parent_container=parent_mc, relation=relation, key=key)
                models.add(child)
                mcs[child] = child_mc
            else:
                # A child can only have one parent, so in order for the child to exist already, it itself must be a parent of something
                child_mc = mcs[child]
                child_mc.set_parent(parent_mc)
        self.importer = None
        if file:
            self.importer = importer_class(models, ignore_existing = ignore_existing, file=file)
        self.mcs = mcs
        self.models = models
        self.relations = relations
        self.data_read = False
        
    def read(self):
        if self.importer:
            from copy import deepcopy
            cleaned_data = deepcopy(self.importer.cleaned_data)
            for model, mc in self.mcs.items():
                mc.data = cleaned_data.get(model, [])
            self.data_read = True
        
    def save(self):
        if self.data_read:
            for mc in self.mcs.values():
                if not mc.saved:
                    mc.save()
                if not mc.saved_m2m:
                    mc.save_m2m()
        
class ModelContainer(object):
    
    def __init__(self, model, parent_container = None, relation=None, key = 'release_id'):
        self.model = model
        self.rel = relation
        self.parent_container = self.parent = parent_container
        self.related_containers = [] # Needed for iterating down/recursively up the relations
        self.key = key
        if self.parent_container:
            self.parent_container.related_containers.append(self)
        self.data = []
        self._key_id_map = {}
        
        self.saved = False
        self.saved_m2m = False if self.parent else True
        
    def get_save_order(self):
        if self.parent:
            return [self, self.parent]
        else:
            return [self]
        
    def set_parent(self, parent_container):
        if self.parent_container:
            self.parent_container.related_containers.remove(self)
            self.parent_container = self.parent = None
        if parent_container:
            self.parent_container =  self.parent = parent_container
            self.parent_container.related_containers.append(self)
        
    @property
    def key_id_map(self):
        if not self._key_id_map:
            # Build release_id_map if any children look up the key (release_id)
            for d in self.data:
                for k in d[self.key]:
                    self._key_id_map[k] = d
        return self._key_id_map
        
    @property
    def instances(self):
        if self.saved:
            for i in self.key_id_map.values():
                yield i['instance']
                    
        
    def get_instance_data(self, data, key):
        instance_data = {k:v for k, v in data.items() if k in self.model.get_basefields(True)}
        
        # Add ForeignKey data to the instance_data
        for mc in self.related_containers:
            if mc.rel.many_to_many == False:
                if not mc.saved:
                    mc.save()
                instance_data[mc.rel.field.name] = mc.key_id_map[key]['instance']
        
        if self.key in instance_data:
            # Special case: self.model == audio: key (here: release_id) is part of the audio model - but it lives as a list in data
            instance_data[self.key] = instance_data[self.key][0]
        return instance_data
        
        
    def save(self):
        with transaction.atomic():
            for d in self.data:
                if not self.rel:
                    for k in d[self.key]:
                        # create an instance PER key PER data item
                        instance_data = self.get_instance_data(d, k)
                        instance = self.model(**instance_data)
                        instance.save()
                        new_d = d.copy()
                        new_d['instance'] = instance
                        self.key_id_map[k] = new_d
                else:
                    # create an instance per data item
                    instance_data = self.get_instance_data(d, 0)
                    instance = None
                    if self.model.objects.filter(**instance_data).count()==1:
                        instance = self.model.objects.filter(**instance_data).first()
                    if not instance:
                        instance = self.model(**instance_data)
                        instance.save()
                    d['instance'] = instance
        self.saved = True
        
    def save_m2m(self):
        records = []
        if self.saved and self.parent and self.rel.many_to_many:
            if not self.parent.saved:
                self.parent.save()
            target_model = self.rel.through
            manager = target_model._default_manager
            source_field_name = self.rel.field.m2m_field_name() # name of 'source' ForeignKey Field on the through model
            target_field_name = self.rel.field.m2m_reverse_field_name()
        
            parent_is_source = target_model._meta.get_field(source_field_name).related_model == self.parent.model
            for d in self.data:
                child_instance = d['instance']
                for k in d[self.key]:
                    #child_instance = self.key_id_map[k]['instance']
                    parent_instance = self.parent.key_id_map[k]['instance']
                    
                    if parent_is_source:
                        source_instance = parent_instance
                        target_instance = child_instance
                    else:
                        source_instance = child_instance
                        target_instance = parent_instance
                        
                    m2m_instance_data = {source_field_name: source_instance, target_field_name: target_instance}
                    if manager.filter(**m2m_instance_data).exists():
                        # Avoiding UNIQUE Constraints violations
                        continue
                    records.append(target_model(**m2m_instance_data)) 
                    
            manager.bulk_create(records)
            
        self.saved_m2m = True

        return records
    
