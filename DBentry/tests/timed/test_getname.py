from .base import *
    
from DBentry.utils import concat_limit
    
def get_name_fully_instance_based(self, **name_data):
    #TODO: use the name_data, Luke
    if not self.pk:
        return "Keine Angaben zu dieser Ausgabe!"
    #print('ausgabe: getting name')
    info = concat_limit(str(self.info).split(), width = LIST_DISPLAY_MAX_LEN+5, sep=" ")
    if self.sonderausgabe and self.info:
        return info
    jahre = concat_limit([jahr[2:] if i else jahr for i, jahr in enumerate([str(j.jahr) for j in self.ausgabe_jahr_set.all()])], sep="/")
    if not jahre:
        if self.jahrgang:
            jahre = "Jg.{}".format(str(self.jahrgang))
        else:
            jahre = "k.A." #oder '(Jahr?)'
      
    if self.magazin.ausgaben_merkmal:
    #TODO: not have this return str(None) if ausgaben_merkmal is set but the user does not provide a value
        merkmal = self.magazin.ausgaben_merkmal
        if merkmal == 'e_datum' and self.e_datum:
            return str(self.e_datum)
        set = getattr(self, 'ausgabe_{}_set'.format(merkmal))
        if set.exists():
            if merkmal == 'monat':
                return "{0}-{1}".format(jahre,"/".join([str(m.monat.abk) for m in set.all()]))
            if merkmal == 'lnum':
                if jahre != "k.A.":
                    jahre = " ({})".format(jahre)
                    return concat_limit(set.all(), sep = "/") + jahre
                else:
                    return concat_limit(set.all(), sep = "/")
            return "{0}-{1}".format(jahre, concat_limit(set.all(), sep = "/", z=2))
            
    num = concat_limit(self.ausgabe_num_set.all(), sep="/", z=2)
    if num:
        return "{0}-{1}".format(jahre, num)
        
    monate = concat_limit(self.ausgabe_monat_set.values_list('monat__abk', flat=True), sep="/")
    if monate:
        return "{0}-{1}".format(jahre, monate)
        
    lnum = concat_limit(self.ausgabe_lnum_set.all(), sep="/", z=2)
    if lnum:
        if jahre == "k.A.":
            return lnum
        else:
            return "{0} ({1})".format(lnum, jahre)
            
    if self.e_datum:
        return str(self.e_datum)
    elif self.info:
        return info
    else:
        return "Keine Angaben zu dieser Ausgabe!"
        
def get_name_partially_instance_based(self, **name_data):
    # uses name_data
    if not self.pk:
        return "Keine Angaben zu dieser Ausgabe!"
    self.info = name_data.pop('info', None) or self.info
    self.sonderausgabe = name_data.pop('sonderausgabe', None) or self.sonderausgabe
    info = concat_limit(str(self.info).split(), width = LIST_DISPLAY_MAX_LEN+5, sep=" ")
    if self.sonderausgabe and self.info:
        return info
    jahre = concat_limit([jahr[2:] if i else jahr for i, jahr in enumerate([str(j.jahr) for j in self.ausgabe_jahr_set.all()])], sep="/")
    self.jahrgang = name_data.pop('jahrgang', None) or self.jahrgang
    if not jahre:
        if self.jahrgang:
            jahre = "Jg.{}".format(str(self.jahrgang))
        else:
            jahre = "k.A." #oder '(Jahr?)'
    
    self.magazin = name_data.pop('magazin', None) or self.magazin
    if self.magazin.ausgaben_merkmal:
    #TODO: not have this return str(None) if ausgaben_merkmal is set but the user does not provide a value
        merkmal = self.magazin.ausgaben_merkmal
        if merkmal == 'e_datum' and self.e_datum:
            return str(self.e_datum)
        set = getattr(self, 'ausgabe_{}_set'.format(merkmal))
        if set.exists():
            if merkmal == 'monat':
                return "{0}-{1}".format(jahre,"/".join([str(m.monat.abk) for m in set.all()]))
            if merkmal == 'lnum':
                if jahre != "k.A.":
                    jahre = " ({})".format(jahre)
                    return concat_limit(set.all(), sep = "/") + jahre
                else:
                    return concat_limit(set.all(), sep = "/")
            return "{0}-{1}".format(jahre, concat_limit(set.all(), sep = "/", z=2))
            
    num = concat_limit(self.ausgabe_num_set.all(), sep="/", z=2)
    if num:
        return "{0}-{1}".format(jahre, num)
        
    monate = concat_limit(self.ausgabe_monat_set.values_list('monat__abk', flat=True), sep="/")
    if monate:
        return "{0}-{1}".format(jahre, monate)
        
    lnum = concat_limit(self.ausgabe_lnum_set.all(), sep="/", z=2)
    if lnum:
        if jahre == "k.A.":
            return lnum
        else:
            return "{0} ({1})".format(lnum, jahre)
    self.e_datum = name_data.pop('e_datum', None) or self.e_datum
    if self.e_datum:
        return str(self.e_datum)
    elif self.info:
        return info
    else:
        return "Keine Angaben zu dieser Ausgabe!"
        
from django.db.models import *
from django.db.models.functions import Substr
def get_name_queryset_based(self):
    updated_required = self.filter(_changed_flag=True)
    
    # info + sonderausgabe
    with_sonder = updated_required.filter(sonderausgabe=True).exclude(info='', info__isnull=True)
    with_sonder.update(_changed_flag=False, _name=Substr('info', 1, LIST_DISPLAY_MAX_LEN+5))
    
    # magazin.ausgaben_merkmal
    
    # sets
    
    # rest
    
        
class TestTimedCNGetName(TimedTestCase, DataTestCase):
    
    file_name = "timed_test_getname.txt"
    model = ausgabe
    test_data_count = 100
    add_relations = True
    
    def setUp(self):
        super().setUp()
        # Force a name update with the most required operations possible (lnum sets)
        self.queryset.update(_name='Time me!')
        
    def test_default(self):
        # Times the current implementation
        self.time(self.queryset.values_list, '_name', func_name='current implementation')
    
    def test_time_get_name_fully_instance_based(self):
        self.model.get_name = get_name_fully_instance_based
        self.time(self.queryset.values_list, '_name', func_name='get_name_fully_instance_based')
        
    def test_get_name_partially_instance_based(self):
        self.model.get_name = get_name_partially_instance_based
        self.time(self.queryset.values_list, '_name', func_name='get_name_partially_instance_based')
        
    
