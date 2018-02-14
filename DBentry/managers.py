from django.db import models
from django.db.utils import OperationalError

from .printer.printer import *

class MIZQuerySet(models.QuerySet):
    
    def has_duplicate(self, original):
        #TODO: WIP
        pass

    def values_all(self, flds, ids = None):
        qs = self
        base_ids = ids or qs.values_list(qs.model._meta.pk.name, flat = True)               # all ids
        rslt = []
        if isinstance(flds, str):
            flds = [f.strip() for f in flds.split(",")]
        for id in base_ids:
            object_values = {'pk':id}
            obj = qs.filter(pk=id)
            for fld in flds:
                values = [i for i in obj.values_list(fld, flat = True)]
                object_values[fld] = values
            yield object_values
            rslt.append(object_values)
        return rslt
        
    def resultbased_ordering(self):
        return self
    
    def create_val_dict(self, key, value, tuplfy=True):
        qs = self
        dict_by_key = {}
        dict_by_val = {}
        for k, v in qs.values_list(key, value):
            try:
                dict_by_key[k].add(v)
            except:
                dict_by_key[k] = set()
                dict_by_key[k].add(v)
            if not tuplfy:
                try:
                    dict_by_val[v].add(k)
                except:
                    dict_by_val[v] = set()
                    dict_by_val[v].add(k)
        if tuplfy:
            for k, v in dict_by_key.items():
                v = tuple(v)
                dict_by_key[k] = v
                try:
                    dict_by_val[v].add(k)
                except:
                    dict_by_val[v] = set()
                    dict_by_val[v].add(k)
        return dict_by_key, dict_by_val

class AusgabeQuerySet(MIZQuerySet):
    def bulk_add_jg(self, jg = 1):
        qs = self
        years = qs.values_list('ausgabe_jahr__jahr', flat = True).order_by('ausgabe_jahr__jahr').distinct()
        last_year = years.first()
        for year in years:
            jg += year - last_year
            loop_qs = qs.filter(ausgabe_jahr__jahr=year)
            try:
                loop_qs.update(jahrgang=jg)
            except Exception as e:
                raise e
            # Do not update the same issue twice (e.g. issues with two years)
            qs = qs.exclude(ausgabe_jahr__jahr=year)
            
            last_year = year
            
    def filter(self, *args, **kwargs):
        # Overridden, to better deal with poorly formatted e_datum values
        if 'e_datum' in kwargs:
            from django.core.exceptions import ValidationError
            try:
                return super(AusgabeQuerySet, self).filter(*args, **kwargs)
            except ValidationError:
                from datetime import datetime
                v = kwargs.get('e_datum', '')
                for possible_formatting in ["%d.%m.%Y", "%d.%m.%y","%Y.%m.%d", "%Y-%m-%d", "%y-%m-%d"]: 
                    # See if the value given for e_datum fits any of the possible formats
                    try:
                        v = datetime.strptime(v, possible_formatting).date()
                    except ValueError:
                        continue
                    break
                # If we couldn't 'fix' the e_datum value, the queryset still contains the faulty value
                # and upon calling super, will raise an exception
                kwargs['e_datum'] = v
        return super(AusgabeQuerySet, self).filter(*args, **kwargs)
       
    def resultbased_ordering(self):
        if not self.query.where.children:
            # Only try to find a better ordering if we are not working on the entire ausgabe queryset 
            # (that is: if filtering has been done)
            return self
        from django.db.models import Min, Max
        self = self.annotate(
                jahr = Min('ausgabe_jahr__jahr'), 
                num = Min('ausgabe_num__num'), 
                lnum = Min('ausgabe_lnum__lnum'), 
                monat = Min('ausgabe_monat__monat_id'), 
                )
        temp = []
        from .models import magazin, ausgabe_num, ausgabe_lnum, ausgabe_monat
        for ausg_detail, detail_name in [(ausgabe_num, 'num'), (ausgabe_lnum, 'lnum')]:
            c = ausg_detail.objects.filter(ausgabe__in=self).values('ausgabe_id').distinct().count()
            temp.append((c, detail_name))
        temp.append(    (self.filter(e_datum__isnull=False).values('e_datum').count(), 'e_datum')   )
        temp.sort(reverse=True)
        ordering = [i[1] for i in temp]
        
        mag_ids = self.values_list('magazin_id', flat = True).distinct()
        if mag_ids.count()==1:
            merkmal = magazin.objects.get(pk=mag_ids.first()).ausgaben_merkmal
            if merkmal:
                if merkmal in ordering:
                    ordering.remove(merkmal)
                ordering.insert(0, merkmal)
         #NOTE: using these annotations caused an exception in BulkConfirmationView when updating its queryset
         # had to reset its order_by
         # maybe something isn't quite loading from inside a view?
        ordering = ['jahr'] + ordering + ['monat', 'sonderausgabe']
        return self.order_by(*ordering)
        
    def print_qs(self):
        qs = self
        flds = ['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_monat__monat']
        alias = ['Jahr','Nummer','lfd.Nummer','Monat']
        columns = list(zip(flds, alias))
        obj_values = qs.values_all(flds)
        for fld, alias in columns:
            if all(all(value is None for value in row[fld]) for row in obj_values):
                # Don't print columns whose rows are all None
                columns.remove((fld, alias))
        print_tabular(obj_values, columns)
        
