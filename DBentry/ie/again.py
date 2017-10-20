import csv
import re

from DBentry.models import *
from DBentry.utils import multisplit, split_field

from .name_utils import *


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
    }
}

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
                
    def print_reader(self, row_number = 0):
        for c, row in enumerate(self.read()):
            if row_number and c == row_number:
                break
            print(row)
                
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
        self.release_id_map = release_id_map
        if ignore_existing:
            self.existing_release_ids = set([id for id in audio.objects.values_list('release_id', flat = True) if id])
            
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
                    if not model in self._cleaned_data:
                        self._cleaned_data[model] = []
                    if model in map_models:
                        # Do these later right from the release_id_map
                        continue
                    for row_number,  data in self.read_file():
                        for processed_data in self.process_row(data, model):
                            if processed_data:
                                self._cleaned_data[model].append(processed_data)
            self.include_id_map()
        return self._cleaned_data
        
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
        
        if int(data.get('release_id', 0)) in self.existing_release_ids:
            return []
            
        data = self.clean_row(data, model)
        
        # TODO: add release_id if not present in data
        
        # A single read row might be split up into a list of data-sets by the model_clean_func if it exists
        if data and not isinstance(data, (list, tuple)):
            data = [data]
        
        return data
    
    def clean_row(self, data, model):
        for k, v in data.items():
            field_clean_func = getattr(self, 'clean_field_{}_{}'.format(k, model._meta.model_name), self._clean_field_basic)
            if callable(field_clean_func):
                data[k] = field_clean_func(v)
        model_clean_func = getattr(self, 'clean_model_{}'.format(model._meta.model_name), None)
        if callable(model_clean_func):
            # model_clean_func WILL return a list(data)!!
            return model_clean_func(data)
        return [data]
            
    def _clean_field_basic(self, value):
        if isinstance(value, str):
            return value.strip()
        return value
        
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
            
    def save_related(self):
        pass
            
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
        self.seps += ['/', '-', '·']    
        
    def _clean_field_basic(self, value):
        value = super(DiscogsImporter, self)._clean_field_basic(value)
        p = re.compile(r'.\(\d+\)') # Look for a whitespace followed by '(number)' -- OR r'.(\d).'? TODO: . ANY CHARACTER!!
        return p.sub('', value)
    
    def clean_model_plattenfirma(self, data):
        return split_field('name', data, self.seps)
        
    def clean_model_format(self, data):
        #TODO: FINISH IT!!
        # incoming string might look like 7xLP,RE,Mono + 2x12",Album,Quad
        # (\d+x: qty) (format_typ) (format_tag) (channel) + ...
        rslt = []
        release_id = data.get('release_id', '0')
        for format_item in data.get('Format', '').split("+"):
            # TODO: use re.split
            if not format_item:
                continue
            
            if 'x' in format_item and format_item.split('x')[0].strip().isnumeric(): 
                anzahl = format_item.split('x')[0].strip()
                format_item = " ".join(format_item.split('x')[1:])
            else:
                anzahl = '1'
                
            format_items = [i.strip()  for i in format_item.split(",")]
            format_typ = format_items.pop(0)
            
            channel = ''
            format_tags = []
            choices = [i[0] for i in Format.CHANNEL_CHOICES]
            for item in format_items:
                if item in choices:
                    channel = item
                else:
                    format_tag.append(item)
                    
            
            rslt.append(dict(release_id=release_id, Format=format_item))
        return rslt
        
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
        
        
class ModelContainer(object):
    
    def __init__(self, model, parent_container = None, key = 'release_id'):
        self.model = model
        self.rel = ''
        self.parent_container = parent_container
        self.related_containers = [] # Needed for iterating down/recursively up the relations
        self.key = key
        if self.parent_container:
            self.parent_container.related_containers.append(self)
        self.data = []
        self._key_id_map = {}
        
    @property
    def key_id_map(self):
        if not self._key_id_map:
            # Build release_id_map if any children look up the release_id
            for d in self.data:
                for rid in d[self.key]:
                    self._key_id_map[rid] = d
        return self._key_id_map
        
        
def save():
    records = []
    for d in mc.data:
        instance_data = {k:v for k, v in d.items() if k not in [mc.key, 'instance']}
        instance = mc.model(**instance_data)
        records.append(instance)
        
    mc.model.objects.bulk_create(records)
    if mc.parent:
        for d in mc.data:
            instance_data = {k:v for k, v in d.items() if k not in [mc.key, 'instance']}
            d['instance'] = mc.model.objects.filter(**instance_data).first()
            child_instance = d['instance']
            for rid in d[self.key]:
                parent_data = parent.key_id_map[rid]
                parent_instance = parent_data['instance']
                
                if self.rel.many_to_many:
                    # Not going to rely on ManyRelatedManagers since those cannot deal with intermediary m2m models
                    target_model = self.rel.through
                    manager = target_model._default_manager
                    source_field_name = self.rel.field.m2m_field_name()
                    target_field_name = self.rel.field.m2m_reverse_field_name()
                    if target_model._m
                    
                    manager.bulk_create([target_model(**{source_field_name:, target_field_name:})])
                else:
                    set_name = self.rel.get_accessor_name()
                    # Get the RelatedManager for the reverse ManyToOne Relation 
                    # The manager can be accessed through the accessor_name from the parent_instance OR the child_instance
                    # but not both (obviously, the 'forward' bit of the relation does not have/need a manager)
                    manager = getattr(parent_instance, set_name, None) or getattr(child_instance, set_name)
                    if manager.instance == parent_instance: # NOTE: does this ONLY compare pk's? 
                        manager.add(child_instance)
                    else:
                        manager.add(parent_instance)
                    
                    
                if is_foreign_key:
                    if hasattr(parent_instance, self.related_set):
                        # ForeignKey field is on the parent's side (child has m2m to parent)
                        set = getattr(parent_instance, self.m2m_set_name)
                        set.add(d['instance'])
                    else:
                        # ForeignKey field is on the child's side (parent has m2m to child)
                        set = getattr(d['instance'], self.m2m_set_name)
                        set.add(parent_instance)
                else:
                    set.bulk_create()
        
