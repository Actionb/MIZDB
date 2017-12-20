from DBentry.models import *

def ausgabe_data(cls):
    cls.model = ausgabe
    instance_list = []
    tmag = magazin.objects.create(magazin_name='Testmagazin')
    lo1 = lagerort.objects.create(ort='TestLagerOrt')
    lo2 = lagerort.objects.create(ort='TestLagerOrt2')
    prov = provenienz.objects.create(geber=geber.objects.create(name='TestCase'))
    
    obj1 = ausgabe(magazin=tmag)
    obj1.save()
    obj1.ausgabe_jahr_set.create(jahr=2000)
    obj1.ausgabe_num_set.create(num=1)
    obj1.bestand_set.create(lagerort=lo1, provenienz = prov)
    instance_list.append(obj1)
    
    obj2 = ausgabe(magazin=tmag, info='Testmerge')
    obj2.save()
    obj2.ausgabe_jahr_set.create(jahr=2000)
    obj2.ausgabe_num_set.create(num=2)
    obj2.bestand_set.create(lagerort=lo1)
    obj2.bestand_set.create(lagerort=lo2, provenienz = prov)
    instance_list.append(obj2)
    
    obj3 = ausgabe(magazin=tmag)
    obj3.save()
    obj3.ausgabe_jahr_set.create(jahr=2000)
    obj3.ausgabe_num_set.create(num=3)
    obj3.bestand_set.create(lagerort=lo2)
    instance_list.append(obj3)
    cls.instance_list = instance_list[:]
    
