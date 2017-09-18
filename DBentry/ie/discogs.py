import csv
import re

from DBentry.models import *
from DBentry.utils import multisplit, split_field

from .name_utils import *

FILE_NAME = '/home/philip/DB/Discogs Export/miz-ruhr2-collection-20170731-0402.csv'
FILE_NAME_WIN = 'ImportData/miz-ruhr2.csv'
MODELS_ALL = [audio, plattenfirma, musiker, band, Format, 
            audio.plattenfirma.through, audio.musiker.through, audio.band.through,
        ]

tag_dict = {
    audio : {
        'Title' : 'titel', 
        'Released' : 'e_jahr', 
        'Catalog#' : 'catalog_nr',
        'release_id' : 'release_id', 
    }, 
    plattenfirma : {
        'Label' : 'name', 
    }, 
    musiker : {
        'Artist' : 'kuenstler_name'
    }, 
    band : {
        'Artist' : 'band_name'
    }, 
    Format : {
        'Format' : 'Format'
    }
}

class DiscogsReader(object):
    
    def __init__(self, file_path = None, tags = {}, reader = csv.DictReader):
        self.file = open(file_path if file_path else FILE_NAME)
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
                
class DiscogsImporter(object):
    
    release_id_map = {}
    
    def __init__(self, models, file_path = None, seperators = [',']):
        if not isinstance(models, (list, tuple)):
            self.models = [models]
        else:
            self.models = models
        if not isinstance(seperators, (list, tuple)):
            self.seps = [seperators]
        else:
            self.seps = seperators
            
        self.file_path = file_path or FILE_NAME
        self.reader = DiscogsReader(self.file_path)
        self._cleaned_data = {}
            
    def read_file(self):
        for c, row in enumerate(self.reader.read()):
            yield c, row
    
#    def get_reader(self):
#        return DiscogsReader(self.file_path)
    
    @property
    def cleaned_data(self):
        if not self._cleaned_data:
            self._cleaned_data = {}
            if self.models:
                for model in self.models:
                    if not model in self._cleaned_data:
                        self._cleaned_data[model] = []
                    for row_number,  data in self.read_file():
                        for processed_data in self.process_row(data, model):
                            if processed_data:
                                self._cleaned_data[model].append((row_number, processed_data))
        return self._cleaned_data
        
    def process_row(self, row_data, model):
            #TODO: read all rows, decide per row what to do (what fields to keep, which ones to modify etc.)
        tags = tag_dict.get(model, {})
        data = {tags.get(k, k):v for k, v in row_data.items() if k in tags}
        
        data = self.clean_row(data, model)
        
            
        # A single read row might be split up into a list of data-sets by the clean function
        if not isinstance(data, (list, tuple)):
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
            for row_number, row_data in rows:
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
            
class X(DiscogsImporter):
    
    
    musiker_list, band_list, rest_list = ([], [], [])
    
    
    def __init__(self, *args, **kwargs):
        super(X, self).__init__(*args, **kwargs)
        self.seps += ['/', '-']    
        
    def _clean_field_basic(self, value):
        value = super(X, self)._clean_field_basic(value)
        p = re.compile(r'.\(\d+\)') # Look for a whitespace followed by '(number)' -- OR r'.(\d).'? TODO: . ANY CHARACTER!!
        return p.sub('', value)
    
    def clean_model_plattenfirma(self, data):
        return split_field('name', data, self.seps)
        
    def clean_model_format(self, data):
        # incoming string might look like 7xLP,RE,Mono + 2x12",Album,Quad
        # (\d+x: qty) (format_typ) (format_tag) (channel) + ...
        rslt = []
        for format_item in data.get('Format', '').split("+"):
            # TODO: use re.split
            if not format_item:
                continue
            if len(format_item.split("x"))>1: #TODO: BAD this would split stuff like "LP, RE, Thatxtag"!!
                anzahl = format_item.split("x")[0].strip()
                format_item = " ".join(format_item.split("x")[1:])
            else:
                anzahl = '1'
            format_typ = format_item.split(",")[0].strip()
            
        return rslt
        
    def clean_model_musiker(self, data):
        rslt = []
        for d in split_field('kuenstler_name', data, self.seps):
            name = d.get('kuenstler_name', '')
            if not name or name in self.band_list or name in self.rest_list:
                continue
            if not name in self.musiker_list:
                x = band_or_musiker(name)
                if x == -1:
                    self.musiker_list.append(name)
                else:
                    if x==1:
                        self.band_list.append(name)
                    else:
                        self.rest_list.append(name)
                    continue
            rslt.append(d)
        return rslt
            
        
    def clean_model_band(self, data):
        rslt = []
        for d in split_field('band_name', data, self.seps):
            name = d.get('band_name', '')
            if not name or name in self.musiker_list or name in self.rest_list:
                continue
            if not name in self.band_list:
                x = band_or_musiker(name)
                if x == 1:
                    self.band_list.append(name)
                else:
                    if x==-1:
                        self.musiker_list.append(name)
                    else:
                        self.rest_list.append(name)
                    continue
            rslt.append(d)
        return rslt
        
        
def test_reader(model = audio):
    return DiscogsReader(model, open('/home/philip/DB/Discogs Export/miz-ruhr2-collection-20170731-0402.csv'))

def test_muba():
    d = [i['Artist'] for i in DiscogsReader().read()]
    return split_MuBa(d)
