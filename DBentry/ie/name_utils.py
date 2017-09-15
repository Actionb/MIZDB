
import re
from DBentry.models import *

band_keywords = [
    'the', 'and', 'group', 'with', 'band', 'duo', 'trio', 'quintet', 'quintett', 
    'quartet', 'quartett', 'all', 'stars', 'ensemble', 'allstars', 'his', 'orchestra', 'orchester', 'orchestre', 'for', 'of', 'to', 
    'der', 'die', 'das', 'und', 'mit', 'seine', 'ihre', 
]

pattern = r'\b{}\b'

vornamen = [p for p in person.objects.values_list('vorname', flat=True).distinct() if p.strip()]
nachnamen = list(person.objects.values_list('nachname', flat=True).distinct())
kuenstler_namen = list(musiker.objects.values_list('kuenstler_name', flat=True).distinct())
band_namen = list(band.objects.values_list('band_name', flat=True).distinct()) + list(band_alias.objects.values_list('alias', flat=True).distinct())

# Remove empty names and names that cause problems with regex
for name_list in [vornamen, nachnamen, kuenstler_namen, band_namen]:
    for n in name_list:
        if not n.strip():
            name_list.remove(n)
        try:
            re.compile(pattern.format(n))
        except:
            name_list.remove(n)

def is_band(name):
    if any(re.search(pattern.format(keyword), name, re.IGNORECASE) for keyword in band_keywords) or \
        any(re.search(pattern.format(bn), name, re.IGNORECASE) for bn in band_namen):
        band_namen.insert(0, name)
        return True
    return False
    
def is_musiker(name):
    for name_list in [kuenstler_namen, vornamen, nachnamen]:
        if any(re.search(pattern.format(n), name, re.IGNORECASE) for n in name_list):
            kuenstler_namen.insert(0, name)
            return True
    return False
    
def band_or_musiker(name):
    if is_band(name):
        return '1'
    if is_musiker(name):
        return '-1'
    return '0'
    
def split_MuBa(name_list):
    musiker = []
    bands = []
    rest = []
    for name in name_list:
        x = band_or_musiker(name)
        if x == 1:
            bands.append(name)
        elif x == -1:
            musiker.append(name)
        else:
            rest.append(name)
    return musiker, bands, rest
