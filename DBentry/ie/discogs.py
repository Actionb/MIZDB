#

from DBentry.models import *
from DBentry.ie.utils import split_field

from .name_utils import *
from .reader import CSVReader

def dict_to_tuple(d):
    return tuple((k, v) for k, v in d.items())
    
def tuple_to_dict(t):
    return {k:v for k, v in t}


db_tags = FormatTag.objects.values_list('abk', flat=True)
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
                if item in db_tags:
                    format_tags.append(item)
    
    return anzahl, channel, format_typ, format_size, format_tags
    
        
def clean_format_related(data, model):
        # incoming string might look like 7xLP,RE,Mono + 2x12",Album,Quad
        # (\d+x: qty) (format_typ) (format_tag) (channel) + ...
    rslt = []
    for format_item in data.get('Format', '').split("+"):
        anzahl, channel, format_typ, format_size, format_tags = tokenize_format(format_item)
        token_dict = dict(anzahl=anzahl, channel=channel, typ=format_typ, size=format_size)
        if model == FormatTag:
            for abk in format_tags:
                rslt.append(dict(abk=abk))
        elif model == FormatSize:
            rslt.append(dict(size=format_size))
        elif model == FormatTyp:
            rslt.append(dict(typ=format_typ))
        else:
            rslt.append(dict(anzahl=anzahl, channel=channel))
    return rslt

class DiscogsImporter(object):
        
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
        
    musiker_list, band_list, rest_list = ({}, {}, {})
    existing_release_ids = set()
            
    def __init__(self, models, file_path = None, file = None, seperators = [',', ' / ', ' - ', ' · '], ignore_existing = True):
        self.models = models
        self.seps = seperators
            
        self.reader = CSVReader(file_path = file_path, file = file)
        self._cleaned_data = {}
        if ignore_existing:
            self.existing_release_ids = set([str(id) for id in audio.objects.values_list('release_id', flat = True) if id])
            
    def read_file(self):
        for c, row in enumerate(self.reader.read(), 2):
            yield c, row
            
    @property
    def cleaned_data(self):
        if not self._cleaned_data:
            self._cleaned_data = {}
            if self.models:
                for model in self.models:
                    data_seen = {} # Maps seen data to the index of that data in self._cleaned_data[model]
                    if not model in self._cleaned_data:
                        self._cleaned_data[model] = []
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
        return self._cleaned_data
        
    def process_row(self, row_data, model):
        tags = self.tag_dict.get(model, {})
        data = {tags.get(k, k):v for k, v in row_data.items() if k in tags or k == 'release_id'}
            
        data = self.clean_row(data, model)
        
        # A single read row might be split up into a list of data-sets by the model_clean_func if it exists
        if data and not isinstance(data, (list, tuple)):
            data = [data]
        
        # Strip release_id 
        for d in data:
            # Not all clean_row funcs keep the release_id, hence the try-catch
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
        p = re.compile(r'.\(\d+\)') # Look for a whitespace followed by '(number)' -- OR r'.(\d).'? TODO: . ANY CHARACTER!!
        return p.sub('', value)
        
    def clean_field_audio_e_jahr(self, value):
        if value == '0':
            return None
            
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
            
