import csv

from DBentry.models import *

FILE_NAME = '/home/philip/DB/Discogs Export/miz-ruhr2-collection-20170731-0402.csv'
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
                    elif k == 'release_id':
                        return_row['release_id'] = v
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
    
    def __init__(self, models, file_path = None):
        if not isinstance(models, (list, tuple)):
            self.models = [models]
        else:
            self.models = models
        self.file_path = file_path or FILE_NAME
        self._cleaned_data = {}
            
    def read_file(self, tags = {}):
        for c, row in enumerate(self.get_reader(tags).read()):
            yield c, row
    
    def get_reader(self, tags = {}):
        return DiscogsReader(self.file_path, tags = tags)
    
    @property
    def cleaned_data(self):
        if not self._cleaned_data:
            if self.models:
                for model in self.models:
                    tags = tag_dict.get(model, {})
                    self._cleaned_data[model] = [(row_number, data) for row_number, data in self.read_file(tags)]
        return self._cleaned_data
      
    def save(self):
        from django.core.exceptions import FieldDoesNotExist
        from django.forms.models import model_to_dict
        for model, rows in self.cleaned_data.items():
            records_total = []
            records_new = []
            for row_number, row_data in rows:
                data = row_data.copy()
                # Verify that we do not have keys in data that are not represented by fields in the model
                for key in row_data.keys():
                    try:
                        model._meta.get_field(key)
                    except FieldDoesNotExist:
                        del data[key]
                if model.objects.filter(**data).exists():
                    record = model.objects.filter(**data).first()
                else:
                    record = model(**data)
                    if records_total:
                        for record, row_data in records_total:
                            
                    if not record in records_new:
                        records_new.append(record)
                    #record.save()
                records_total.append((record, row_data))
                
#                # Create preliminary release_id_map, record might not have a value for pk yet!
#                r_id = row_data.get('release_id')
#                if r_id:
#                    if not self.release_id_map.get(r_id):
#                        self.release_id_map[r_id] = {}
#                    self.release_id_map[r_id][model] = record
            
            try:
                model.objects.bulk_create(records_new)
                print("Saved via bulk_create")
            except:
                print("Saving each")
                for record in records_new:
                    record.save()
                    
            print("Setting up release_id_map")
            for record, row_data in records_total:
                r_id = row_data.get('release_id')
                if r_id:
                    if not self.release_id_map.get(r_id):
                        self.release_id_map[r_id] = {}
                    if record.pk:
                        self.release_id_map[r_id][model] = record
                    else:
                        # Either saved via bulk or not saved at all
                        model_instance = model.objects.filter(**model_to_dict(record)).first()
                        if model_instance:
                            self.release_id_map[r_id][model] = model_instance
            print("saved {} records of model {}".format(len(records_new), model._meta.model_name))
            
class DiscogsFullImporter(DiscogsImporter):
    
    def process_row(self, row):
        for model in self.models:
            for tag in self.tag_dict[model]:
                stuff[model][tag] = row.get(tag)
                
        
        
def test_reader(model = audio):
    return DiscogsReader(model, open('/home/philip/DB/Discogs Export/miz-ruhr2-collection-20170731-0402.csv'))
