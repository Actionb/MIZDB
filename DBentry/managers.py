from django.db import models
from django.db.utils import OperationalError

from .printer import *

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
            object_values = {'id':id}
            obj = qs.filter(pk=id)
            for fld in flds:
                values = [i for i in obj.values_list(fld, flat = True)]
                object_values[fld] = values
            #yield object_values
            rslt.append(object_values)
        return rslt
    
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
        
