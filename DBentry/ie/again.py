import csv
import re

from DBentry.models import *
from DBentry.utils import multisplit, split_field, tuple_to_dict, dict_to_tuple

from .name_utils import *

from django.db import transaction


MODELS_ALL = [audio, plattenfirma, musiker, band, Format, 
            audio.plattenfirma.through, audio.musiker.through, audio.band.through,
        ]

tag_dict = {
    audio : {
        'Title' : 'titel', 
        'Released' : 'e_jahr', 
        'Catalog#' : 'catalog_nr',
    }, 
    plattenfirma : {
        'Label' : 'name', 
    }, 
    musiker : {
        'Artist' : 'kuenstler_name', 
    }, 
    band : {
        'Artist' : 'band_name', 
    }, 
    Format : {
        'Format' : 'Format', 
    }, 
    FormatTag : {
        'Format' : 'Format',
    }, 
    FormatSize : {
        'Format' : 'Format',
    }, 
    FormatTyp : {
        'Format' : 'Format',
    }, 
    
}

def save_order(mc_list):
    if len(mc_list)==1:
        if mc.parent:
            return [mc, mc.parent]
        else:
            return [mc]
    order = []
    for mc in mc_list:
        if mc.parent:
            if mc.rel.many_to_many:
                pass
            else:
                # MC is child with a ForeignKey on parent pointing at it
                pass
    
    return order

def tokenize_format(format_item):
    anzahl = '1'
    channel = ''
    format_typ = 'Vinyl'
    format_size = 'LP'
    format_tags = []
    
    if format_item:
        if 'x' in format_item and format_item.split('x')[0].strip().isnumeric(): 
            anzahl = format_item.split('x')[0].strip()
            format_item = " ".join(format_item.split('x')[1:])
            
        format_items = [i.strip()  for i in format_item.split(",")]
        format_size = format_items.pop(0)
        
        format_tags = []
        choices = [i[0] for i in Format.CHANNEL_CHOICES]
        for item in format_items:
            if item in choices:
                channel = item
            else:
                format_tags.append(item)
    
    return anzahl, channel, format_typ, format_size, format_tags
    
        
def clean_format_related(data, model):
        # incoming string might look like 7xLP,RE,Mono + 2x12",Album,Quad
        # (\d+x: qty) (format_typ) (format_tag) (channel) + ...
    rslt = []
    #release_id = data.get('release_id', '0')
    for format_item in data.get('Format', '').split("+"):
        anzahl, channel, format_typ, format_size, format_tags = tokenize_format(format_item)
        token_dict = dict(anzahl=anzahl, channel=channel, typ=format_typ, size=format_size)
        if model == FormatTag:
            for abk in format_tags:
                #rslt.append(dict(release_id=release_id, abk=abk))
                rslt.append(dict(abk=abk))
        elif model == FormatSize:
            #rslt.append(dict(release_id=release_id, size=format_size))
            rslt.append(dict(size=format_size))
        elif model == FormatTyp:
            #rslt.append(dict(release_id=release_id, typ=format_typ))
            rslt.append(dict(typ=format_typ))
        else:
            #rslt.append(dict(release_id=release_id, anzahl=anzahl, channel=channel))
            rslt.append(dict(anzahl=anzahl, channel=channel))
    return rslt

class DiscogsReader(object):
    
    def __init__(self, file_path = None, file = None, tags = {}, reader = csv.DictReader):
        self.file = file or open(file_path if file_path else FILE_NAME)
        self.reader = reader
        
        if isinstance(tags, (list, tuple)):
            tags = {tags[0]:tags[0]}
        if isinstance(tags, str):
            tags = {tags:tags}
        self.tags = tags
        
    def get_reader(self):
        self.file.seek(0)
        return self.reader(self.file)
    
    def read(self):
        for row in self.get_reader():
            if self.tags:
                return_row = {}
                for k, v in row.items():
                    if k in self.tags:
                        return_row[self.tags[k]] = v
                yield return_row
            else:
                yield row
                
    def print_rows(self, row_number = -1, to_file = None):
        for c, row in enumerate(self.read(), 2):
            if c == row_number:
                break
            print(row, file=to_file)
            
    def print_row(self, row_number = -1):
        for c, row in enumerate(self.read(), 2):
            if c == row_number:
                print(row, file=to_file)
                break
                
class BaseImporter(object):
    
    existing_release_ids = set()
            
    def __init__(self, models = None, file_path = None, file = None, seperators = [','], 
                    release_id_map = {}, ignore_existing = True):
        if models:
            self.models = models
        else:
            self.models = set()            
            for x in self.release_id_map.values():
                for model in x.keys():
                    self.models.add(model)
        self.seps = seperators
            
        self.reader = DiscogsReader(file_path = file_path, file = file)
        self._cleaned_data = {}
        self._container_data = {}
        self.release_id_map = release_id_map
        if ignore_existing:
            self.existing_release_ids = set([str(id) for id in audio.objects.values_list('release_id', flat = True) if id])
            
    def read_file(self):
        for c, row in enumerate(self.reader.read(), 2):
            yield c, row
            
    @property
    def cleaned_data(self):
        if not self._cleaned_data:
            self._cleaned_data = {}
            map_models = []
            if self.release_id_map:
                #{<release_id>:{<model>:[<names>]}}
                release_id, model_dict = self.release_id_map.copy().popitem()
                map_models = model_dict.keys()
            if self.models:
                for model in self.models:
                    data_seen = {} # Maps seen data to the index of that data in self._cleaned_data[model]
                    if not model in self._cleaned_data:
                        self._cleaned_data[model] = []
                    if model in map_models:
                        # Do these later right from the release_id_map
                        continue
                    for row_number, data in self.read_file():
                        release_id = data.get('release_id')
                        if release_id in self.existing_release_ids:
                            continue
                        for processed_data in self.process_row(data, model):
                            if processed_data:
                                data_tuple = dict_to_tuple(processed_data)
                                
                                if data_tuple in data_seen:
                                    if release_id not in self._cleaned_data[model][data_seen[data_tuple]]['release_id']:
                                        self._cleaned_data[model][data_seen[data_tuple]]['release_id'].append(release_id)
                                else:
                                    processed_data['release_id'] = [release_id]
                                    index = len(self._cleaned_data[model])
                                    data_seen[data_tuple] = index
                                    self._cleaned_data[model].append(processed_data)
            self.include_id_map()
        return self._cleaned_data
        
                
        
    @property
    def container_data(self):
        if not self._container_data:
            for model, rows in self.cleaned_data.items():
                data_list 
                self._container_data[model] = []
                for data in rows:
                    pass
        
    def include_id_map(self):
        if self.release_id_map:
            # Reset cleaned data when using this function from outside cleaned_data()
            for models in self.release_id_map.values():
                for model in models:
                    self._cleaned_data[model] = []
            #{<release_id>:{<model>:[<names>]}}
            for release_id, models in self.release_id_map.items():
                for model, names in models.items():
                    if model == person:
                        dict_list = []
                        for name in names:
                            last_space = name.find(" ", -1)
                            vorname = name[:last_space]
                            nachname = name[last_space+1:]
                            dict_list.append({'release_id':release_id, 'vorname':vorname, 'nachname':nachname})
                    else:
                        field_name = tag_dict.get(model).get('Artist')
                        dict_list = [{'release_id':release_id, field_name:name} for name in names]
                    self.cleaned_data[model].append(dict_list)
        
    def process_row(self, row_data, model):
        tags = tag_dict.get(model, {})
        data = {tags.get(k, k):v for k, v in row_data.items() if k in tags or k == 'release_id'}
        
#        if int(data.get('release_id', 0)) in self.existing_release_ids:
#            return []
            
        data = self.clean_row(data, model)
        
        # TODO: add release_id if not present in data
        
        # A single read row might be split up into a list of data-sets by the model_clean_func if it exists
        if data and not isinstance(data, (list, tuple)):
            data = [data]
        
        # Strip release_id 
        for d in data:
            try:
                del d['release_id']
            except:
                pass
        
        return data
    
    def clean_row(self, data, model):
        for k, v in data.items():
            field_clean_func = getattr(self, 'clean_field_{}_{}'.format(model._meta.model_name.lower(), k), self._clean_field_basic)
            if callable(field_clean_func):
                data[k] = field_clean_func(v)
        model_clean_func = getattr(self, 'clean_model_{}'.format(model._meta.model_name.lower()), None)
        if callable(model_clean_func):
            # model_clean_func WILL return a list(data)!!
            return model_clean_func(data)
        return [data]
            
    def _clean_field_basic(self, value):
        if isinstance(value, str):
            return value.strip()
        return value
        
    def clean_field_audio_e_jahr(self, value):
        if value == '0':
            return None
        
    def save(self):
        from django.core.exceptions import FieldDoesNotExist
        for model, rows in self.cleaned_data.items():
            records_total = []
            records_new = []
            data_seen = []
            for row_data in rows:
                if model.objects.filter(**row_data).exists():
                    record = model.objects.filter(**row_data).first()
                else:
                    record = model(**row_data)
                    if not row_data in data_seen:
                        records_new.append(record)
                data_seen.append(row_data)
                records_total.append((record, row_data))
            
            try:
                model.objects.bulk_create(records_new)
            except:
                for record in records_new:
                    record.save()
                    
            print("saved {} records of model {}".format(len(records_new), model._meta.model_name))
            
    def extract_data(self, models):
        extract = {}
        for model in models:
            if model in self.models:
                extract[model] = self.cleaned_data.get(model)
        return extract
            
class DiscogsImporter(BaseImporter):
    
    
    musiker_list, band_list, rest_list = ({}, {}, {})
    
    
    def __init__(self, *args, **kwargs):
        super(DiscogsImporter, self).__init__(*args, **kwargs)
        self.seps = [',', ' / ', ' - ', ' · ']    
        
    def _clean_field_basic(self, value):
        value = super(DiscogsImporter, self)._clean_field_basic(value)
        p = re.compile(r'.\(\d+\)') # Look for a whitespace followed by '(number)' -- OR r'.(\d).'? TODO: . ANY CHARACTER!!
        return p.sub('', value)
    
    def clean_model_plattenfirma(self, data):
        return split_field('name', data, self.seps)
        
    def clean_model_formatsize(self, data):
        return clean_format_related(data, FormatSize)
        
    def clean_model_formattyp(self, data):
        return clean_format_related(data, FormatTyp)
        
    def clean_model_format(self, data):
        return clean_format_related(data, Format)
        
    def clean_model_formattag(self, data):
        return clean_format_related(data, FormatTag)
        
    def clean_model_musiker(self, data):
        rslt = []
        for d in split_field('kuenstler_name', data, self.seps):
            name = d.get('kuenstler_name', '')
            release_id = d.get('release_id', '0')
            if not name or name in self.band_list or name in self.rest_list:
                if name in self.band_list:
                    self.band_list[name].add(release_id)
                if name in self.rest_list:
                    self.rest_list[name].add(release_id)
                continue
                
            if not name in self.musiker_list:
                x = band_or_musiker(name)
                if x == -1:
                    self.musiker_list[name] = set([release_id])
                else:
                    if x==1:
                        self.band_list[name] = set([release_id])
                    else:
                        self.rest_list[name] = set([release_id])
                    continue
            rslt.append(d)
        return rslt
            
        
    def clean_model_band(self, data):
        rslt = []
        for d in split_field('band_name', data, self.seps):
            name = d.get('band_name', '')
            release_id = d.get('release_id', '0')
            if not name or name in self.musiker_list or name in self.rest_list:
                if name in self.musiker_list:
                    self.musiker_list[name].add(release_id)
                if name in self.rest_list:
                    self.rest_list[name].add(release_id)
                continue

            
            if not name in self.band_list:
                x = band_or_musiker(name)
                if x == 1:
                    self.band_list[name] = set([release_id])
                else:
                    if x==-1:
                        self.musiker_list[name] = set([release_id])
                    else:
                        self.rest_list[name] = set([release_id])
                    continue
            rslt.append(d)
        return rslt
        
class FullImporter(object):
        
    def __init__(self, file):
        models = [audio, Format, FormatTyp, FormatSize, NoiseRed, FormatTag, plattenfirma, audio.plattenfirma.through]
        self.file = file
        #super(FullImporter, self).__init__(models, file=file)
        
    def import_all(self):
        i = DiscogsImporter(models = [audio], file=self.file)
        i.save()
        
        i = DiscogsImporter(models = [plattenfirma], file=self.file)
        i.save()
        
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
#            for mc in self.mcs.values():
#                mc.save_related()
        
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
#        if not self.saved:
#            self.save()
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
#            for d in self.data:
#                if 'instance' in d:
#                    yield d['instance']
                    
        
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
#    
#    def save_related(self):
#        if self.parent: # and self.parent.saved
#            if not self.parent.saved:
#                self.parent.save()
#            for d in self.data:
#                if 'instance' not in d:
#                    print(d)
#                    instance_data = self.get_instance_data(d)
#                    d['instance'] = self.model.objects.filter(**instance_data).first()
#                    #d['instance'] = self.model.objects.get(**instance_data)
#                child_instance = d['instance']
#                    
#                if self.rel.many_to_many:
#                    records = []
#                    # Not going to rely on ManyRelatedManagers since those cannot deal with intermediary m2m models
#                    target_model = self.rel.through
#                    manager = target_model._default_manager
#                    source_field_name = self.rel.field.m2m_field_name() # name of 'source' ForeignKey Field on the through model
#                    target_field_name = self.rel.field.m2m_reverse_field_name()
#                    
#                    
#                    
#                    # ManyToManyField can be on either side of the through model (or even both sides) 
#                    parent_is_source = target_model._meta.get_field(source_field_name).related_model == self.parent.model
#                    for k in d[self.key]:
#                        #parent_data = self.parent.key_id_map[k]
#                        parent_instance = self.parent.key_id_map[k]#parent_data['instance']
#                        if parent_is_source:
#                            source_instance = parent_instance
#                            target_instance = child_instance
#                        else:
#                            source_instance = child_instance
#                            target_instance = parent_instance
#                        
#                        if manager.filter(**{source_field_name: source_instance, target_field_name: target_instance}).exists():
#                            # Avoiding UNIQUE Constraints violations
#                            continue
#                        records.append(target_model(**{source_field_name: source_instance, target_field_name: target_instance})) 
#                    try:
#                        manager.bulk_create(records)
#                    except:
#                        for record in records:
#                            try:
#                                record.save()
#                            except:
#                                print(record)
#                                print(manager.all())
#                else:
#                    # child_instance (self) is at the reverse end (m2m connections defined by values in d[self.key]) of the ForeignKey
#                    # parent_instance.model contains the ForeignKey
#                    # use child_instance.RelatedManager to add relations
#                    set_name = self.rel.get_accessor_name()
#                    manager = getattr(child_instance, set_name)
#                    for k in d[self.key]:
#                        #parent_data = self.parent.key_id_map[k]
#                        parent_instance = self.parent.key_id_map[k]#parent_data['instance']
#                        manager.add(parent_instance)
#                        
#        self.saved_related = True

    
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
#            try:
#                manager.bulk_create(records)
#            except:
#                for record in records:
#                    try:
#                        record.save()
#                    except:
#                        print(getattr(record, source_field_name))
#                        print(getattr(record, target_field_name))
            
        self.saved_m2m = True

        return records
    
#        if self.parent: # and self.parent.saved
#            if not self.parent.saved:
#                self.parent.save()
#            for d in self.data:
#                records = []
#                for k in d[self.key]:
#    #                if 'instance' not in d:
#    #                    print(d)
#    #                    instance_data = self.get_instance_data(d)
#    #                    #d['instance'] = self.model.objects.filter(**instance_data).first()
#    #                    #d['instance'] = self.model.objects.get(**instance_data)
#                    child_instance = self.key_id_map[k]
#                        
#                    if self.rel.many_to_many:
#                        # Not going to rely on ManyRelatedManagers since those cannot deal with intermediary m2m models
#                        target_model = self.rel.through
#                        manager = target_model._default_manager
#                        source_field_name = self.rel.field.m2m_field_name() # name of 'source' ForeignKey Field on the through model
#                        target_field_name = self.rel.field.m2m_reverse_field_name()
#                        
#                        
#                        
#                        # ManyToManyField can be on either side of the through model (or even both sides) 
#                        parent_is_source = target_model._meta.get_field(source_field_name).related_model == self.parent.model
#    #                    for k in d[self.key]:
#    #                        #parent_data = self.parent.key_id_map[k]
#                        parent_instance = self.parent.key_id_map[k]#parent_data['instance']
#                        if parent_is_source:
#                            source_instance = parent_instance
#                            target_instance = child_instance
#                        else:
#                            source_instance = child_instance
#                            target_instance = parent_instance
#                            
#                        if manager.filter(**{source_field_name: source_instance, target_field_name: target_instance}).exists():
#                            # Avoiding UNIQUE Constraints violations
#                            continue
#                        records.append(target_model(**{source_field_name: source_instance, target_field_name: target_instance})) 
#
#                    else:
#                        # child_instance (self) is at the reverse end (m2m connections defined by values in d[self.key]) of the ForeignKey
#                        # parent_instance.model contains the ForeignKey
#                        # use child_instance.RelatedManager to add relations
#                        set_name = self.rel.get_accessor_name()
#                        manager = getattr(child_instance, set_name)
#                        for k in d[self.key]:
#                            #parent_data = self.parent.key_id_map[k]
#                            parent_instance = self.parent.key_id_map[k]#parent_data['instance']
#                            manager.add(parent_instance)
#                if records:
#                    try:
#                        manager.bulk_create(records)
#                    except:
#                        for record in records:
#                            try:
#                                record.save()
#                            except:
#                                print(record)
#                                print(manager.all())
