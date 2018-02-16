
import re
from DBentry.models import *

band_keywords = [
    'the', 'and', 'group', 'with', 'band', 'los', 
    'all', 'stars', 'ensemble', 'allstars', 'his', 'orchestra', 'orchester', 'orchestre', 'for', 'of', 'to', 
    'der', 'die', 'das', 'und', 'mit', 'seine', 'ihre', 'choire', 'chor', 'corps', 'korps', 
    'duo', 'trio', 'quartet', 'quartett', 'quintet', 'quintett', 'sextett', 'sestet', 'sextet', 'sextette', 
    'swingtett', 'ballet', 'music', 'musik', 'new', 'neu'
]

pattern = r'\b({})\b'
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
pattern_kuenstler_namen = re.compile(pattern.format("|".join(kuenstler_namen)), re.IGNORECASE)
pattern_vornamen = re.compile(pattern.format("|".join(vornamen)), re.IGNORECASE)
pattern_nachnamen = re.compile(pattern.format("|".join(nachnamen)), re.IGNORECASE)

#TODO: use re.escape() to deal with bad strings?
def band_or_musiker(name):
    # Stage 0: Look for band keywords or numbers in name
    # TODO: look for " 's "? (Jane's Addiction)
    if re.search(r'&', name) or re.search(r'\d+', name) or pattern_band_kwds.search(name):
        band_namen.insert(0, name)
        return 1
    
    # Stage 1: exact matches
    b = name in band_namen
    m = name in kuenstler_namen
    if b != m:
        # name exactly matched either a band_name or a kuenstler_name, but not both
        if b:
            band_namen.insert(0, name)
            return 1
        elif m:
            kuenstler_namen.insert(0, name)
            return -1
    # Either the name exactly matched a band_name AND a kuenstler_name, or neither
    # Stage 2: Determine whether the name is a proper name (pre- + surname); if so, it's probably a musiker
    has_vorname = False
    has_nachname = False
    if len(name.split())>1:
        v = name.split()[0]
        n = " ".join(name.split()[1:])
        has_vorname = v in vornamen
        has_nachname = n in nachnamen
        if has_vorname and has_nachname:
            # vorname and nachname matched exactly: definitely a 'person', ergo NOT a band
            kuenstler_namen.insert(0, name)
            return -1
        if has_vorname or has_nachname:
            # Stage 2a: exact vorname match OR exact nachname match
            # ==> Strong indication that the name is a proper,real name
            if b:
                # Stage 1 resulted in two exact matches, but name is most likely a musiker since it has either a real vorname or nachname
                kuenstler_namen.insert(0, name)
                return -1
            else:
#                re_match_nn = pattern_nachnamen.search(n)
#                re_match_vn = pattern_vornamen.search(v)
                # Stage 1 resulted in no matches, and all we have is that name contains either a proper vorname or nachname
                if has_vorname:
                    if pattern_nachnamen.search(n) or any(re.search(pattern.format(v), kn, re.IGNORECASE) for kn in kuenstler_namen):
                        # exact vorname + partial nachname OR exact vorname + partial kuenstler_namen
                        kuenstler_namen.insert(0, name)
                        return -1
                if has_nachname:
                    if pattern_vornamen.search(v) or any(re.search(pattern.format(n), kn, re.IGNORECASE) for kn in kuenstler_namen):
                        # exact nachname + partial vorname OR exact nachname + partial kuenstler_namen
                        kuenstler_namen.insert(0, name)
                        return -1
        else:
            # vor+/nachname either only matches partially or not at all to items in lists vornamen, nachnamen
            # partial matches in those two lists hold very little value compared to partial matches in kuenstler_namen,band_namen
            pass
        # possible outcomes of Stage 2a that have made it this far:
        # exact vorname OR nachname but stage 1 returned no exact matches in either kuenstler_namen or band_namen
        # exact vorname and no partial nachname (and vice versa)
        # no/possibly only partial matches of vorname and nachname
        
    # name cannot be a proper name, it only consists of one word
    #  -- OR it may be a proper name but earlier attempts at finding out for certain were inconclusive
    # b == True, m == True || b == False, m == False
    
    # Name is a single word, assign it to bands.
    # While there are musiker with just a word for their kuenstler_name, they hard to distinguish from bands with the same
    # properties. If name was a musiker AND was found as exact match, we already have dealt with that.
    if len(name.split())==1:
        band_namen.insert(0, name)
        return 1
    
    # Stage 3: Exact matches in vor- or nachname and partial match in kuenstler_namen
    re_match_kn = False 
    if has_vorname or has_nachname:
        re_match_kn = pattern_kuenstler_namen.search(name)
        if re_match_kn:
            # Exact vor- or nachname and a partial match in kuenstler_namen
            kuenstler_namen.insert(0, name)
            return -1
    
    # Stage 4: Drop the idea of name being a possible real name; resolve the case where b = m == True (two exact matches)
    # Favour band_namen over kuenstler_namen because band_namen tend to be more distinctive (as in wacky)
    if b:
        band_namen.insert(0, name)
        return 1
        
    # Stage 5: All we have left is looking for partial matches in band_namen or kuenstler_namen
    # To assure that we at least get a decently fitting match, we need to compare the word counts of the matches and name
    # If word_count(partial match)<word_count(name): look for a better match (e.g. band 'Jane' vs name 'Jane Manning')
    word_count_name = len(name.split())
    
    # NOTE: is it even worth using pattern_band_namen if we are going to need a proper list anyway?
    bn_matches = []
    if pattern_band_namen.search(name):
        bn_matches = [
                bn for bn in band_namen 
                if re.search(pattern.format(bn), name, re.IGNORECASE) and \
                len(bn.split()) >= word_count_name
            ]        
    kn_matches = []
    if re_match_kn == False:
        re_match_kn = pattern_kuenstler_namen.search(name)
    if re_match_kn:
        kn_matches = [
                kn for kn in kuenstler_namen
                if re.search(pattern.format(kn), name, re.IGNORECASE) and \
                len(kn.split()) >= word_count_name
            ]
    
    #Compare partial matches and find the best fit
    if not bn_matches and not kn_matches:
        # Not even a partial match in either list, flag as rest
        return 0
    # Exact match in word_count, again favouring band_namen
    if any(len(match.split())==word_count_name for match in bn_matches):
        band_namen.insert(0, name)
        return 1
    if any(len(match.split())==word_count_name for match in kn_matches):
        kuenstler_namen.insert(0, name)
        return -1
        
    # Last hope: ANY partial matches. if there are no partial matches in band_namen there MUST be a partial match in kuenstler_namen
    # (no match in either was already handled)
    if bn_matches:
        band_namen.insert(0, name)
        return 1
    kuenstler_namen.insert(0, name)
    return -1
    
def split_MuBa(name_list):
    musiker = []
    bands = []
    rest = []
    for name in name_list:
        if any(name in l for l in [musiker, bands, rest]):
            print(name+':duplicate')
            continue
        print(name, end=":")
        x = band_or_musiker(name)
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
    
def split_name(name):
    """ Splits a full name into pre- and surname while accounting for certain name-specific keywords like 'von' or 'van de'
        or 'Senior', etc.
    """
    kwds = [r'\bvan\b', r'\bvan.der\b', r'\bvan.de\b', r'\bde\b', r'\bvon\b',r'\bvan.den\b'
            r'\bSt\.?', r'\bSaint\b', r'\bde.la\b', r'\bla\b'] 
    jrsr = [r'\bJunior\b', r'\bJr\.?', r'\bSenior\b', r'\bSr\.?',  r'\bIII\.?', r'\bII\.?'] #r'\b.I.'
    for w in kwds:
        p = re.compile(w, re.IGNORECASE)
        sep = re.search(p, name)
        if sep:
            
            sep = sep.start()
            v = name[:sep].strip()
            n = name[sep:].strip()
            return v, n
    suffix = None
    for w in jrsr:
        p = re.compile(w, re.IGNORECASE)
        sep = re.search(p, name)
        if sep:
            suffix = name[sep.start():sep.end()]
            name = name[:sep.start()]+name[sep.end():]
    v = " ".join(name.strip().split()[:-1]).strip()
    n = name.strip().split()[-1]
    if suffix:
        n = n + " " + suffix
    if len(n)<3:
        # ... and v: ? For if the nachname is just weird, but still a proper name (since it has a proper vorname, too)
        if n.endswith('.') or len(n)==1:
            # Bsp: Mark G. --> not a proper name
            v = None
            n = None
    return v, n
    
