
from django.db.models.fields import FieldDoesNotExist
from django.core.exceptions import ValidationError

from data_importer.importers import XMLImporter

from DBentry.models import *

from .reader import MIZReader
   
DBentry_fields = {
#bundesland : get_main_fields(bundesland), 
#land : get_main_fields(land), 
}    

 
#TODO: INSPECT CHOICES!!! --> benutze vllt nicht get_field(x).choices sondern ein lokales Array
#TODO: FKEYS--> suche nach ID fails: suche nach cleaned_data **values ohne ID
class MIZImporter(XMLImporter):
    verbose = True
    validate_fkey = True
    distinct = False
    redirect = False
    root = ''
    file_path = 'ExportData/logs/'
    exclude_existing = True
    model = None 
        
    def __init__(self, source = None, model = None, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v) 
        if model:
            self.model = model
            self.Meta.model = model
        if source:
            if "." not in source:
                if '.' not in self.file_path and self.model:
                    self.file_path += '{}.txt'.format(source+self.model._meta.model_name)
                if not self.root:
                    self.root = source
                source = 'ExportData/{0}.xml'.format(source)
        try:
            self.file = open(self.file_path, 'w')
        except:
            self.file = None
        self.read_row_counter = 0
        super(MIZImporter, self).__init__(source)
        
        self.exists = []
        self.error_list = []
        self.duplicates = []
        self.skipped = {'exists':self.exists, 'error':self.error_list, 'duplicate':self.duplicates}
        
    
    
    def set_reader(self):
        self._reader = MIZReader(self)
            
    def get_reader(self):
        if not self._reader:
            self.set_reader()
        return self._reader
        
    def reader_rslt(self, convert_tags = True, find = ''):
        if find:
            rslt = []
            for i in self.get_reader().read(convert_tags=convert_tags):
                for j in i.values():
                    if j.find(str(find)) != -1:
                        rslt.append(i)
                        break
            return rslt
        return [i for i in self.get_reader().read(convert_tags=convert_tags)]
        
    def print_reader(self, convert_tags = True, find = ''):
        [print(i) for i in self.reader_rslt(convert_tags = convert_tags, find = find)]
        
    def print_data(self, find=None):
        if find:
            if isinstance(find, dict):
                [print(i) for i in self.find(**find)]
            else:
                [print(i) for i in self.find(find)]
        else:
            [print(i) for i in self.cleaned_data]
    
    def _read_file(self):
        """
        Create cleaned_data content
        """
        if not isinstance(self._reader, list):
            reader = self._reader.read()
        else:
            reader = self._reader
            
        for row, values in enumerate(reader, 1):
            self.read_row_counter+=1
            if self.Meta.ignore_first_line:
                row -= 1
            if self.Meta.starting_row and row < self.Meta.starting_row:
                pass
            elif row < 1:
                pass
            else:
                if self.verbose:
                    print("\n Processing row {}: ".format(row), values, file=self.file)
                yield self.process_row(row, values)

    def process_row(self, row, values):
        """
        Read clean functions from importer and return tupla with row number, field and value
        """
        from data_importer.core.exceptions import StopImporter
        has_error = False

        if self.Meta.ignore_empty_lines:
            # ignore empty lines
            if not any(values.values()):
                return None
        
        if self.verbose:
            print("Cleaning fields...", file=self.file)
        for k, v in values.items():
            if self.Meta.raise_errors:
                values[k] = self.clean_field(k, v)
            else:
                try:
                    values[k] = self.clean_field(k, v)
                except StopImporter as e:
                    raise StopImporter(self.get_error_message(e, row))
                except Exception as e:
                    #self._error.append(self.get_error_message(e, row))
                    self.skipped['error'].append((values, 'Error: Cleaning fields failed. {}'.format(e)))
                    has_error = True

        if has_error:
            if self.verbose:
                print("Processing failed: has_error: {} \n".format(self.skipped['error'][-1]), file=self.file)
            return None
        if self.verbose:
            print("Fields cleaned: ", values, file=self.file)

        # validate full row data
        if self.verbose:
            print("Cleaning rows...", file=self.file)
        try:
            values = self.clean_row(values)
        except Exception as e:
            #self._error.append(self.get_error_message(e, row))
            self.skipped['error'].append((values, 'Error: Cleaning rows failed. {}'.format(e)))
            return None
        
        if values == None:
            if self.verbose:
                print("Processing failed: Returned None on clean_row. \n", file=self.file)
            return None
        if self.verbose:
            print("Row cleaned: {} \n".format(values), file=self.file)
        return (row, values)
    
    def clean_row(self, values):
            
        if self.model:
            
            if self.model == person:
                # Don't create undistinguishable 'unbekannt' person sets...
                # Let the autor/musiker record deal with the person's creation
                if 'nachname' in values.keys() and values['nachname'] == 'unbekannt':
                    return None
            
            # Create persons for autor and musiker but not for band mitglieder
            if self.model in [autor, musiker] and not self.source.endswith('bands.xml'):
                
                if self.verbose:
                    print("Setting Autor/Musiker person_id for {}...".format(values), file=self.file)
                # Lookup person
                name_dict = {k:v for k, v in values.items() if k in ['vorname', 'nachname']}
                herkunft_dict = {k:v for k, v in values.items() if k == 'herkunft_id'}
                pfiltered = person.objects
                d = name_dict.copy()
                d.update(herkunft_dict)
                p = person(**d)
                if name_dict:
                    if pfiltered.filter(**name_dict).exists():
                        pfiltered = pfiltered.filter(**name_dict)
                        if pfiltered.count() == 1:
                            p = pfiltered[0]
                        else:
                            if herkunft_dict and pfiltered.filter(**herkunft_dict).count() == 1:
                                p = pfiltered.get(**herkunft_dict)
                            else:
                                if self.model == autor:
                                    print("Error: Could not find a concrete match for Autor/Musiker {}!".format(values),  file = self.file)
                                    print("Choices are: {}".format(pfiltered), file=self.file)
                                    self.skipped['error'].append((values, 'No concrete person match.'))
                                    return None

                if p:
                    # Person found, adjust values
                    new_values = dict(values)
                    if 'vorname' in new_values:
                        del new_values['vorname']
                    if 'nachname' in new_values:
                        del new_values['nachname']
                    if 'herkunft_id' in new_values:
                        del new_values['herkunft_id']
                    if p.pk is None:
                        print("Autor/Musiker person_id not found. Delaying person creation until .save()", file=self.file)
                    else: 
                        print("Autor/Musiker person_id set to {} ({})".format(p.pk, p), file=self.file)
                    new_values['person'] = p
                    values = new_values
                else:
                    # Something went very wrong
                    pass
        
            # Bei Magazinen konnte man sowohl ein Land als auch einen Ort angeben.
            # Wir müssen diese beiden zusammenfassen, wenn ein Land aber kein Ort gegeben war.
            if self.model == magazin:
                if 'country_id' in values.keys():
                    new_values = dict(values)
                    if not 'ort_id' in values.keys():
                        # Erstelle einen passenden Ort-Datensatz (ohne Stadt/Bundesland), falls nicht schon vorhanden
                        lid = values['country_id']
                        if not ort.objects.filter(land_id=lid, stadt='', bland_id__isnull=True).exists():
                            if self.verbose:
                                print("Creating ort with land_id {} for {}.".format(lid, values), file=self.file)
                            ort.objects.create(land_id=lid)
                        new_values['ort_id'] = ort.objects.filter(land_id=lid, stadt='', bland_id__isnull=True)[0].id
                        
                    del new_values['country_id']
                    values = new_values
                    
            for fld, value in values.items():
                try:
                    model_field = self.model._meta.get_field(fld)
                except FieldDoesNotExist:
                    pass
                else:
                    # NOT NULL Constraint violated
                    if not values[fld] and not model_field.blank:
                        if self.verbose:
                            print("Error: NOT NULL Constraint violated for field {} with value {}".format(fld, value), file=self.file)
                        self.skipped['error'].append((values, "NOT NULL Constraint failed."))
                        return None
                        
                    
                    # Validate FKEYs
                    if self.validate_fkey:
                        related_model = model_field.related_model
                        if related_model and not model_field.blank:
                            # Use FKEY_ID to verify if the related record exists; return None if it doesn't exist 
                            if isinstance(values[fld], models.Model):
                                pkval = values[fld].pk
                                if pkval is None:
                                    # related object has not been saved yet
                                    continue
                            else:
                                pkval = values[fld]
                            if not related_model.objects.filter(pk=pkval).exists():
                                if self.verbose:
                                    print("Error: clean_row:validate_fkey failed for field {} with value {}".format(fld, pkval), file=self.file)
                                self.skipped['error'].append((values, 'Validate FKEY failed.'))
                                return None
            
            # Record already exists
            
            # Exclude not-yet-existing person 
            v_nop = {}
            for k, v in values.items():
                if isinstance(v, person):
                    if v.pk is None:
                        continue
                v_nop[k] = v
            
            if self.model.objects.filter(**v_nop).exists() and self.exclude_existing:
                if self.verbose:
                    print("Record already exists: ", values, file=self.file)
                self.skipped['exists'].append((values, 'Record already exists.'))
                return None
        
        # Don't return an empty dict
        if values:
            return values
        else:
            return None
                    
    
    def clean_field(self, field_name, value):
        """
        User default django field validators to clean content
        and run custom validates
        """
        from django.db.models.fields.related import ForeignKey
        
        if self.model:
            clean_function = getattr(self, 'clean_{0!s}'.format(field_name), False)

            if clean_function and value:
                try:
                    value = clean_function(value)
                except Exception as msg:
                    default_msg = str(msg).replace('This field', '')
                    new_msg = 'Field ({0!s}) {1!s}'.format(field_name, default_msg)
                    #raise ValidationError(new_msg)
            
            # default django validate field
            try:
                field = self.model._meta.get_field(field_name)
                if field.is_relation and field.related_model:
                    #field = field.foreign_related_fields[0]
                    field = field.related_model._meta.get_field('id')
                field.clean(value, field)
            except FieldDoesNotExist:
                pass  # do nothing if not find this field in model
            except Exception as msg:
                default_msg = msg.messages[0].replace('This field', '')
                new_msg = 'Field ({0!s}) {1!s}'.format(field.name, default_msg)
                raise ValidationError(new_msg)
        return value
    
    def clean_seitenumfang(self, value):
        value = value.replace('.', '')
        sfld = artikel._meta.get_field('seitenumfang')
        try:
            value = sfld.clean(value, sfld)
        except:
            print("Failed to clean value for seitenumfang {}.".format(value), file=self.file)
            raise ValidationError()
        return value
        
    
    def clean_musiker_id(self, value):
        if not value.isnumeric():
            # Ein Künstlername wurde übergeben und keine ID
            m = musiker.objects.filter(kuenstler_name=value)
            if m.exists():
                if m.count()>1:
                    print("WARNING: multiple musiker found with name {}.".format(value), file=self.file)
                return m[0].pk
            else:
                print("No musiker found with name: {}".format(value), file=self.file)
                return None
        return value
    
            
    def clean_verlag_id(self, value):
        # NOTE: get_or_create?? Lieber nicht: bulk_create ist soviel schneller
        if not value.isnumeric():
            v = verlag.objects.filter(verlag_name=value)
            if v.exists():
                if v.count()>1:
                    print("WARNING: multiple verlage found with name {}.".format(value), file=self.file)
                return v[0].pk
            else:
                print("No verlag found with name: {}".format(value), file=self.file)
                return None
        return value
        
            
            
    def clean_status(self, value):
        return lookup_choice(value, ausgabe._meta.get_field('status'))
        
    def clean_turnus(self, value):
        return lookup_choice(value, magazin._meta.get_field('turnus'))
    
    
    def clean_code(self, code_value):
        try:
            code_field = self.model._meta.get_field('code')
        except FieldDoesNotExist:
            pass
        else:
            if len(code_value)>code_field.max_length:
                if "-" in code_value:
                    code_value = code_value[code_value.find("-")+1:]
                if len(code_value)>code_field.max_length:
                    code_value = code_value[:4]
        return code_value
        
    def clean_datefield(self, value):
        if 'T' in value:
            return value[:value.index('T')]
        else:
            return value
            
    def clean_e_datum(self, value):
        return self.clean_datefield(value)
        
    def clean_erstausgabe(self, value):
        return self.clean_datefield(value)
        
    def clean_land_id(self, value):
        """
        Versuche, kaputte IDs aus Access-Tabellen (welche mit Werten >10000) wieder zu reparieren
        """
        value = str(value)
        if not land.objects.filter(id=value).exists():
                # Rekonstruiere korrekte Land ID aus dem Code Kürzel des originstrings
                if self.model == ort:
                    data = self.reader_rslt(convert_tags = False, find=value)
                    if data:
                        if self.verbose:
                            print("Restoring corrupt/false land_id {}.".format(value), file=self.file)
                        record = data[0]
                        originstring = record['originstring']
                        if "-" in originstring:
                            if "," in originstring:
                                land_code = originstring[originstring.find(',')+2:originstring.find('-')]
                            else:
                                land_code = originstring[originstring.find('-'):]
                        else:
                            land_code = originstring
                        if land.objects.filter(code=land_code).exists():
                            if self.verbose:
                                print("Restored land_id to new value: {}".format(value), file=self.file)
                            value = land.objects.filter(code=land_code)[0].id
                        else:
                            if self.verbose:
                                print("land_id restore failed. Returning None", file=self.file)
                        value = None
                else:
                    if self.verbose:
                        print("clean_land_id: No land found with id {}. Returning None".format(value), file=self.file)
                    return None
        return value
    
    def post_clean(self):
        if self.distinct:
            post_cleaned = []
            distinct_list = []
            for row, values in self._cleaned_data:
                values_noid = {k:v for k, v in values.items() if k != 'id'}
                if values_noid:
                    if distinct_list.count(values_noid) == 0:
                        distinct_list.append(values_noid)
                        post_cleaned.append((row, values))
                    else:
                        self.skipped['duplicate'].append((values_noid, 'Duplicate in distinct set'))
            self._cleaned_data = post_cleaned.copy()
            
            
            
#            
#            for row, values in self._cleaned_data:
#                # TODO: use dict.count()!!! set([x for x in values if values.count(x) > 1]) --> needs dicts without IDs though
##                if any(v.find('unbekannt')!=-1 for v in values.values()):
##                    continue
#                values_noid = {k:v for k, v in values.items() if k not in ['id','original_id']}
#                if values_noid:
#                    match = False
#                    for r, v in post_cleaned:
#                        #Exclude ID from comparison
#                        v_noid = {k:v for k, v in v.items() if k not in ['id','original_id']}
#                        if(v_noid==values_noid):
#                            match = True
#                            self.skipped['duplicate'].append(((values_noid, v_noid), 'Duplicate in distinct set'))
#                            break
#                    if not match:
#                        post_cleaned.append((row, values))
#                else:
#                    if values:
#                        post_cleaned.append((row, values))
#            self._cleaned_data = post_cleaned
    
    def save(self, instance=None, bulk_create = True):
        """
        Save all contents
        DONT override this method
        """
        from django.db.utils import IntegrityError
        if not instance:
            instance = self.model

        if not instance:
            raise AttributeError('Invalid instance model')
        records_saved = 0
        if self.Meta.transaction:
            pass
            # TODO: Make it work
#            with transaction.atomic():
#                for row, data in self.cleaned_data:
#                    record = instance(**data)
#                    try:
#                        record.save()
#                        records_saved+=1
#                    except IntegrityError as e:
#                        self.skipped['error'].append((data, e))
#                        continue
#
#                try:
#                    self.pre_commit()
#                except Exception as e:
#                    self._error.append(self.get_error_message(e, error_type='__pre_commit__'))
#                    transaction.rollback()
#
#                try:
#                    transaction.commit()
#                except Exception as e:
#                    self._error.append(self.get_error_message(e, error_type='__transaction__'))
#                    transaction.rollback()

        else:
            # Create persons
            if any('person' in data.keys() for row, data in self.cleaned_data):
                for row, data in self.cleaned_data:
                    if 'person' in data.keys():
                        # person may point to person() instance to create a new person record
                        p = data['person']
                        if isinstance(p, models.Model) and p.pk is None:
                            try:
                                p.save()
                            except Exception as e:
                                self.skipped['error'].append((data, e))
                                print("Error: Failed to save new person {} ( record: {})".format(p, data), file=self.file)
                                break
            
            if bulk_create:
#                for row, data in self.cleaned_data:
#                    # Stop saving twice on accident
#                    if self.model.objects.filter(**data).exists():
#                        print("Record already exists: {}".format(data), file=self.file)
#                        continue
                records = [instance(**data) for row, data in self.cleaned_data]
                self.model.objects.bulk_create(records)
                records_saved = len(records)
            else:
                for row, data in self.cleaned_data:
                    # Stop saving twice on accident
                    if self.model.objects.filter(**data).exists():
                        print("Record already exists: {}".format(data), file=self.file)
                        continue
                    record = instance(**data)
                    try:
                        record.save(force_update=False)
                        records_saved+=1
                    except Exception as e:
                        self.skipped['error'].append((data, e))
                        continue

        self.post_save_all_lines()
        rtnmsg = """Imported {0} out of {1} cleaned records ({2} records read from file).
Skipped: {3} ({4} records already existed, {5} skipped due to errors, {6} duplicates in read records).""".format(
            records_saved, len(self.cleaned_data), self.read_row_counter, 
            len(self.skipped['error'])+len(self.skipped['exists'])+len(self.skipped['duplicate']), len(self.skipped['exists']), 
            len(self.skipped['error']), len(self.skipped['duplicate'])
            )
        return rtnmsg
    
    def reclean(self):
        self._readed = False
        self.exists.clear()
        self.error_list.clear()
        self.duplicates.clear()
        self.skipped = {'exists':self.exists, 'error':self.error_list, 'duplicate':self.duplicates}
        self.read_row_counter = 0
        self._cleaned_data = ()
        self.cleaned_data
        
    @property
    def count(self):
        return len(self.cleaned_data)
        
    def search(self, to_find = [], tags = []):
        return self._reader.search(to_find = to_find, tags = tags)
        
        
    def find(self, *args, **kwargs):
        rslt = []
        for row, values in self.cleaned_data:
            match = False
            if args:
                for v in values.values():
                    for a in args:
                        try:
                            if v.find(str(a))!=-1:
                                rslt.append((row, values))
                                match = True
                                break
                        except:
                            pass
                    if match:
                        break
            if kwargs:
                for k, v in kwargs.items():
                    if k in values.keys():
                        try:
                            if str(values[k]).find(str(v))!=-1:
                                rslt.append((row, values))
                                match = True
                                break
                        except:
                            pass
                    if match:
                        break
        return rslt
    
    


def lookup_choice(value, choice_field):
    snowflake = {
        '8xjährlich':'m', 
        '2-monatlich' : 'm2', 
        '2-wöchentlich' : 'w2', 
        '5x Jährlich' : 'q', 
        '8-wöchentlich' : 'm2', 
        'Bearbeitung abgeschlossen' : 'abg', 
    }
    if value in snowflake:
        return snowflake[value]
    d = {j:i for i,j in choice_field.choices}
    if value in d:
        return d[value]
    print(value)
    return value

def get_musiker():
    # NOTE: Sinn?
    a = MIZImporter(source='artist')
    vornamen, nachnamen = get_namen()
    return a.search(to_find = list(vornamen)+list(nachnamen))
    
def get_bands():
    a = MIZImporter(source='artist')
    band_keywords = [
        'the', 'and', 'group', 'die', 'with', 'band', 'duo', 'trio', 'quintet', 'quintett', 
        'quartet', 'quartett', 'all', 'stars', 'ensemble', 'allstars', 'his', 'orchestra', 'orchester', 'for', 'of', 'to', 
    ]
    bands = set([i['artist_name'] for i in a.search(to_find=band_keywords)])
    return bands
    
            
if __name__ == '__main__':
    pass

#                name_dict = {k:v for k, v in values.items() if k=='vorname' or k=='nachname'}
#                pfiltered = person.objects.filter(**name_dict)
#                if pfiltered.exists():
#                    p = pfiltered[0]
#                    if pfiltered.count() > 1:
#                        # Try to use the original_id to find the correct person
#                        if 'original_id' in values.keys():
#                            if pfiltered.filter(original_id=values['original_id']).exists():
#                                pfiltered = pfiltered.filter(original_id=values['original_id'])
#                                p = pfiltered[0]
#                        # Still more than one person fits the names, narrow filtering down with herkunft_id
#                        if pfiltered.count() > 1 and 'herkunft_id' in values.keys():
#                            if pfiltered.filter(herkunft=values['herkunft_id']).exists():
#                                p = pfiltered.filter(herkunft=values['herkunft_id'])[0]
