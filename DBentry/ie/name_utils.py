
import re
from DBentry.models import *

band_keywords = [
    'the', 'and', 'group', 'with', 'band', 'duo', 'trio', 'quintet', 'quintett', 
    'quartet', 'quartett', 'all', 'stars', 'ensemble', 'allstars', 'his', 'orchestra', 'orchester', 'orchestre', 'for', 'of', 'to', 
    'der', 'die', 'das', 'und', 'mit', 'seine', 'ihre',  'chor', 'korps'
]

pattern = r'\b({})\b'
#band_keywords = [pattern.format(bn) for bn in band_keywords]
#band_keywords.insert(0, r'&')
pattern_band_kwds = re.compile(pattern.format("|".join(band_keywords)),  re.IGNORECASE)
 

vornamen = [p for p in person.objects.values_list('vorname', flat=True).distinct() if p.strip()]
nachnamen = list(person.objects.values_list('nachname', flat=True).distinct())
kuenstler_namen = list(musiker.objects.values_list('kuenstler_name', flat=True).distinct())
band_namen = list(band.objects.values_list('band_name', flat=True).distinct()) + list(band_alias.objects.values_list('alias', flat=True).distinct())

# Remove empty names and names that cause problems with regex
for name_list in [kuenstler_namen, band_namen, vornamen, nachnamen, ]:
    for n in name_list:
        if not n.strip():
            name_list.remove(n)
        try:
            re.compile(pattern.format(n))
        except:
            name_list.remove(n)

pattern_band_namen = re.compile(pattern.format("|".join(band_namen)), re.IGNORECASE)
pattern_kuenstler_namen = re.compile(pattern.format("|".join(kuenstler_namen + vornamen + nachnamen)), re.IGNORECASE)


def is_band(name, use_regex = False):
    if not name:
        return False
#    if name in band_namen:
#        #NOTE: matches 'Peter Lustig' to 'Peter Lustig Band' if band was evaluated before...
#        return True
    if re.search(r'&', name) or pattern_band_kwds.search(name) or pattern_band_namen.search(name):
        #band_namen.insert(0, name)
        return True
        
#    if any(re.search(keyword, name, re.IGNORECASE) for keyword in band_keywords):
#        band_namen.insert(0, name)
#        return True
#    for bn in band_namen:
#        if len(bn)>3 and bn.lower() in name.lower():
#            band_namen.insert(0, name)
#            return True
#    if use_regex:
#        if any(re.search(pattern.format(bn), name, re.IGNORECASE) for bn in band_namen):
#            band_namen.insert(0, name)
#            return True
    return False
    
def is_musiker(name, use_regex = False):
    if not name:
        return False
#    if name in kuenstler_namen:
#        return True
    if pattern_kuenstler_namen.search(name):
            #kuenstler_namen.insert(0, name)
            return True
        
#    for n in name_list:
#        if len(n)>3 and n.lower() in name.lower():
#            kuenstler_namen.insert(0, name)
#            return True
#    for vn in vornamen:
#        if len(vn)>3 and vn.lower() in name.lower():
#            kuenstler_namen.insert(0, name)
#            return True
#    for nn in nachnamen:
#        if len(nn)>3 and nn.lower() in name.lower():
#            kuenstler_namen.insert(0, name)
#            return True
#    if use_regex:           # das ist Käse
#        if any(re.search(pattern.format(n), name, re.IGNORECASE) for n in kuenstler_namen):
#            kuenstler_namen.insert(0, name)
#            return True
    return False
    
def band_or_musiker(name, use_regex = False):
    #TODO: ORDER MATTERS!!! exact matches first, then partial matches!
    # Jane Manning is assigned to bands because of bands like 'Jane's Addiction' - but Jane Manning also qualifies for being a musiker (is_musiker(Jane MAnning) == True)
    if is_band(name, use_regex):
        return 1
    if is_musiker(name, use_regex):
        return -1
    return 0
    
def split_MuBa(name_list, use_regex = False):
    musiker = []
    bands = []
    rest = []
    for name in name_list:
        if any(name in l for l in [musiker, bands, rest]):
            print(name+':duplicate')
            continue
        print(name, end=":")
        x = band_or_musiker(name, use_regex)
        if x == 1:
            bands.append(name)
            print("band")
        elif x == -1:
            musiker.append(name)
            print("musiker")
        else:
            rest.append(name)
            print("rest")
    return musiker, bands, rest
