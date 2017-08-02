from django.test import TestCase
from .models import *
from .utils import create_val_dict, swap_dict
import re
import timeit
import itertools

def wrapper(func, *args, **kwargs):
    def wrapped():
        return func(*args, **kwargs)
    return wrapped
    
def time(func, nr=1, *args, **kwargs):
    print('Timing {}...'.format(func.__name__))
    print(timeit.timeit(wrapper(func, *args, **kwargs), number=nr))
    print()
# Create your tests here.
    
def print_test():
    m = magazin.objects.get(pk=51)
    qs= m.ausgabe_set.filter(ausgabe_jahr__jahr=1998)
    qs = qs.filter(ausgabe_num__num=1)
    qs.print_qs()


def the_difference():
    def printme(id_set):
        for id in id_set:
            instance = ausgabe.objects.get(pk=id)
            mag = instance.magazin
            years = instance.jahre()
            nums = instance.num_string()#list(instance.ausgabe_num_set.values('num'))
            lnums = instance.lnum_string()#list(instance.ausgabe_lnum_set.values('lnum'))
            months = instance.monat_string()#list(instance.ausgabe_monat_set.values('monat'))
            format_str = "{}\t"*6
            print(format_str.format(instance, mag, years, nums, lnums, months))
    print('Timestuff')
    ts = timestuff()
    print('get_duplicates')
    gd = ausgabe.get_duplicates()
    y = set(itertools.chain(*gd))
    x = set(itertools.chain(*ts))
    xdy = x.difference(y)
    ydx = y.difference(x)
    
    for difset in [xdy, ydx]:
        for id in difset:
            for id_set in ts: #NOTE: <- where's gd?
                if id in id_set:
                    printme(id_set)
                    print()
        print("-"*10)
                
    
    
    

def timestuff():
    #NOTE: KEEP THIS!!
    ids = ausgabe.objects.values_list('id','magazin_id')
    num_by_id,  num_by_num = create_val_dict(ausgabe_num.objects, 'ausgabe_id', 'num')
    lnum_by_id, lnum_by_lnum = create_val_dict(ausgabe_lnum.objects, 'ausgabe_id', 'lnum')
    monat_by_id,  monat_by_monat = create_val_dict(ausgabe_monat.objects, 'ausgabe_id', 'monat')
    ausg_by_mag, mags_by_ausg = create_val_dict(ausgabe.objects, 'magazin_id', 'id', tuplfy=False)
    year_by_ausg, ausg_by_year = create_val_dict(ausgabe_jahr.objects, 'ausgabe_id', 'jahr')
    
    def items_match(id, candidate_id):
        for criteria in [year_by_ausg, num_by_id, lnum_by_id, monat_by_id]:
            try:
                match = criteria[id] == criteria[candidate_id]
            except KeyError:
                continue
            if not match:
                return False
        return True
            
    candidates_per_id = {}
    
    for mag_id, ausg_set in ausg_by_mag.items():
        for id in ausg_set:
            for dict_by_id, dict_by_val in [(num_by_id, num_by_num), (lnum_by_id, lnum_by_lnum), (monat_by_id, monat_by_monat)]:
                if id in dict_by_id:
                    val = dict_by_id[id]
                    if len(dict_by_val[val])>1:
                        for candidate_id in dict_by_val[val]:
                            if mag_id in mags_by_ausg[candidate_id]:
                                if items_match(id, candidate_id):
                                    if not id in candidates_per_id:
                                        candidates_per_id[id] = set()
                                    candidates_per_id[id].add(candidate_id)
    cset = set([tuple(v) for v in candidates_per_id.values() if len(v)>1])
    return cset

if __name__ == '__main__':
    pass
