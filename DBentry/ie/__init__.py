
import re
import xml.etree.ElementTree as et
from collections import namedtuple

from DBentry.models import *

from .importer import *
from .exporter import *
from .reader import *
            
def repair_choices():
    print('\nMagazine...\n')
    mags = MIZImporter(source='journal', model=magazin)
    for m in mags.reader_rslt():
        try:
            db_mag = magazin.objects.get(pk=m['id'])
        except:
            print("No magazine found with ID:", m['id'])
            continue
        if 'turnus' in m:
            db_mag.turnus = lookup_choice(m['turnus'], magazin._meta.get_field('turnus'))
        else:
            db_mag.turnus = 'u'
        db_mag.save()
    print('\nAusgaben...\n')
    ausg = MIZImporter(source='issue', model=ausgabe)
    for a in ausg.reader_rslt():
        try:
            db_ausg = ausgabe.objects.get(pk=a['id'])
        except:
            print("No ausgabe found with ID:", a['id'])
            continue
        if 'status'in a:
            db_ausg.status = lookup_choice(a['status'] , ausgabe._meta.get_field('status'))
        else:
            db_ausg.status = 'unb'
        db_ausg.save()

def get_namen():
    vornamen = set()
    nachnamen = set()
    for p in person.objects.all():
        if len(p.vorname)>2:
            vornamen.add(p.vorname.replace('.', '')) 
        if len(p.nachname)>2:
            nachnamen.add(p.nachname.replace('.', ''))
    return vornamen, nachnamen      
        
def split_artists():
    v, n = get_names()
    band_keywords = [
        'the', 'and', '&', 'group', 'die', 'with', 'band', 'duo', 'trio', 'quintet', 'quintett', 
        'quartet', 'quartett', 'all', 'stars', 'ensemble', 'allstars', 'his', 'orchestra', 'orchester', 'for', 'of', 'to', 
    ]
    
    remove_me = ['edited_on', 'edited_by', 'created_on', 'created_by']
    
    def band_or_musiker(artist_name):
        # artist ist band
        for kwd in band_keywords:
            if '&'  in artist_name or '+' in artist_name or "'s" in artist_name:
                return '1'
            if re.search(r'\b{}\b'.format(kwd), artist_name, re.IGNORECASE):
                return '1'
        # artist ist musiker
        for vn in v:
            if re.search(r'\b{}\b'.format(vn), artist_name, re.IGNORECASE):
                return '-1'
        for nn in n:
            if re.search(r'\b{}\b'.format(nn), artist_name, re.IGNORECASE):
                return '-1'
        # unbekannt
        return '0'
    
    tree = et.parse('ExportData/artist.xml')
    artists = tree.findall('artist')
    rslt = []
    for i, a in enumerate(artists):
        element = et.SubElement(a, 'ist_band')
        element.text = '0'
        artist_name = a.find('artist_name').text
        if artist_name.isalpha() or len(artist_name)>2:
            element.text = band_or_musiker(artist_name)
        for elem in remove_me:
            try:
                a.remove(a.find(elem))
            except:
                pass
        print(i,"Checked {}; set to {}.".format(artist_name, element.text))
    print("\nWriting xml...")
    tree.write('ExportData/musikerbands.xml')

def get_tag_set(source):
    a = MIZImporter(source=source)
    print(a._reader.get_tag_set())
    
    

def rip(x = None):
    if not x:
        x = {'num2': '8', 'num1': '7', 'ausgabe_id': '9015'}
    for k, v in x.items():
        if k != 'ausgabe_id':
            yield {k[:-1]:v, 'ausgabe_id' : x['ausgabe_id']}

def ImportAll(reset=False):
    r = namedtuple('Return', 'genre, musiker, band, autor')
    s = "~"*10 + ' {} ' + "~"*10
    print(s.format('Genres'))
    r.genre = ImportGenres(reset)
    
    print(s.format('Musiker'))
    r.musiker = ImportMusiker(reset)
    
    print(s.format('Bands'))
    r.band = ImportBands(reset)
    
    print(s.format('Autoren'))
    r.autor = ImportAutoren(reset)
    
    return r
    

def ImportArtikel(reset = False):
    a = namedtuple('Artikel', 'Artikel,Genre,Schlagwort,Autor,Musiker,Band')
    if reset:
        print("Lösche Artikel...")
        artikel.objects.all().delete()
        
    print("Importiere Artikel...")
    iart = MIZImporter(source='article', model=artikel)
    artstmt = iart.save(bulk_create=True)
    print(artstmt)
    print("Artikel importiert.\n")
    a.Artikel = iart
    
    print("Importiere Artikel-Genres...")
    iartg = MIZImporter(source='rel_genreXarticle', model = artikel.genre.through, distinct = True)
    print(iartg.save())
    print("Artikel-Genres importiert.\n")
    a.Genre = iartg
    
    print("Importiere Artikel-Schlagwörter...")
    iarts = MIZImporter(source='rel_typeXarticle', model = artikel.schlagwort.through, distinct = True)
    print(iarts.save())
    print("Artikel-Schlagwörter importiert.\n")
    a.Schlagwort = iarts
    
    print("Importiere Artikel-Autoren...")
    iarta = MIZImporter(source='rel_authorXarticle', model = artikel.autor.through, distinct = True)
    print(iarta.save())
    print("Artikel-Autoren importiert.\n")
    a.Autor = iarta
    
    print("Importiere Artikel-Musiker...")
    iartm = MIZImporter(source='rel_artistXarticle', model = artikel.musiker.through, distinct = True)
    print(iartm.save())
    print("Artikel-Musiker importiert.\n")
    a.Musiker = iartm
    
    print("Importiere Artikel-Bands...")
    iartb = MIZImporter(source='rel_artistXarticle', model = artikel.band.through, distinct = True)
    print(iartb.save())
    print("Artikel-Bands importiert.\n")
    a.Band = iartb
    
    
    
    return a

def ImportAusgaben(reset = False):
    if reset:
        print("Lösche Ausgaben...")
        ausgabe.objects.all().delete()
        ausgabe_jahr.objects.all().delete()
        ausgabe_num.objects.all().delete()
        ausgabe_lnum.objects.all().delete()
        ausgabe_monat.objects.all().delete()
        
    print("Importiere Ausgaben...")
    iausg = MIZImporter(source='issue', model=ausgabe)
    astmt = iausg.save(bulk_create = True)
    print(astmt)
    print("Ausgaben importiert.\n")
    
    print("Importiere Ausgaben-Jahre...")
    ijahr = MIZImporter(source='issue', model=ausgabe_jahr)
    jstmt = ijahr.save(bulk_create = True)
    print(jstmt)
    print("Ausgaben-Jahre importiert.\n")
    
    print("Importiere Ausgaben-Nummern...")
    inum = MIZImporter(source='issue', model=ausgabe_num)
    nstmt = inum.save(bulk_create = True)
    print(nstmt)
    print("Ausgaben-Nummern importiert.\n")
    
    print("Importiere Ausgaben-Lfd Nummern...")
    ilnum = MIZImporter(source='issue', model=ausgabe_lnum)
    lnstmt = ilnum.save(bulk_create = True)
    print(lnstmt)
    print("Ausgaben-Lfd Nummern importiert.\n")
    
    print("Importiere Ausgaben-Monate...")
    imon = MIZImporter(source='issue', model=ausgabe_monat)
    mstmt = imon.save(bulk_create = True)
    print(mstmt)
    print("Ausgaben-Monate importiert.\n")
    
    print(astmt)
    print(jstmt)
    print(nstmt)
    print(lnstmt)
    print(mstmt)
    return [iausg, ijahr, inum, ilnum, imon]

def ImportAutoren(reset = False):
    r = namedtuple('Autoren', 'Person, Autor')
    if reset:
        print("Lösche Autoren-Personen...")
        person.objects.filter(autor__isnull=False).delete()
        print("Lösche Autoren...")
        autor.objects.all().delete()
        
    print("Importiere Autor-Personen...")
    iperson = MIZImporter(source='author', model=person, distinct = True) #NOTE: distinct necessary? Ja - für 'unbekannt'
    pstmt = iperson.save(bulk_create = True)
    print(pstmt)
    print("Autor-Personen importiert.\n")
    r.Person = iperson
    
    print("Importiere Autoren...")
    iautor = MIZImporter(source='author', model=autor)
    astmt = iautor.save(bulk_create = True)
    print(astmt)
    print("Autoren importiert.\n")
    r.Autor = iautor
    
    return r
    
def ImportMagazine(reset = False):
    if reset:
        print("Lösche Magazine...")
        magazin.genre.through.objects.all().delete()
        magazin.objects.all().delete()
        verlag.objects.all().delete()
        
    print("Importiere Verläge...")
    iverlag = MIZImporter(source='journal', model=verlag)
    vstmt = iverlag.save()
    print(vstmt)
    print("Verläge importiert.\n")
    
    print("Importiere Magazine...")
    imag = MIZImporter(source='journal', model = magazin)
    mstmt = imag.save()
    print(mstmt)
    print("Magazine importiert.\n")
    
    print("Importiere Magazin-Genres...")
    igenre = MIZImporter(source='rel_genreXjournal', model=magazin.genre.through)
    gstmt = igenre.save()
    print(gstmt)
    print("Magazin-Genres importiert.\n")
    
    print(vstmt)
    print(mstmt)
    print(gstmt)
    return [iverlag, imag, igenre]
    
def ImportOrte(reset = False):
    if reset:
        print("Lösche Orte...")
        land.objects.all().delete()
        bundesland.objects.all().delete()
        ort.objects.all().delete()
        
    print("Importiere Länder...")
    iland = MIZImporter(source='country', model=land)
    lstmt = iland.save(bulk_create=True)
    print(lstmt)
    print("Länder importiert.\n")
    
    print("Importiere Bundesländer...")
    ibland = MIZImporter(source='state', model=bundesland)
    bstmt = ibland.save(bulk_create=True)
    print(bstmt)
    print("Bundesländer importiert.\n")
    
    print("Importiere Orte...")
    iort = MIZImporter(source='origin', model=ort)
    ostmt = iort.save(bulk_create=True)
    print(ostmt)
    print("Orte importiert.\n")
    
    print(lstmt)
    print(bstmt)
    print(ostmt)
    return [iland, ibland, iort]
    
    
def ImportGenres(reset = False):
    g = namedtuple('Genres', 'Genres, Alias')
    if reset:
        print("Lösche Genres...")
        genre_alias.objects.all().delete()
        genre.objects.all().delete()
        
    print("Importiere Genres...")
    igenre = MIZImporter(source='genre', model=genre, distinct = True)
    gstmt = igenre.save(bulk_create=True)
    print(gstmt)
    print("Genres importiert.\n")
    g.Genres=igenre
    
    print("Importiere Genre-Aliase...")
    igenre_alias = MIZImporter(source='genre', model=genre_alias)
    gastmt = igenre_alias.save(bulk_create=True)
    print(gastmt)
    print("Genre-Aliase importiert.\n")
    g.Alias=igenre_alias
    
    return g
    
def ImportMusiker(reset=False):
    m = namedtuple('Musiker', 'Person, Musiker, Alias, Genres')
    #f = open('ExportData/logs/ImportMusiker.txt')
    if reset:
        print("Lösche Musiker...")
        musiker.objects.all().delete()
        print("Lösche Musiker-Personen...\n\n")
        # NOTE: Vorsicht..
        person.objects.filter(autor__isnull=True).delete()
            
    print("Importiere Musiker-Personen...")
    iperson = MIZImporter(source='musiker', root='artist', model = person, distinct = True)
    pstmt = iperson.save(bulk_create=True)
    print(pstmt)
    print("Musiker-Personen importiert.\n")
    m.Person = iperson
    
    print("Importiere Musiker...")
    imus = MIZImporter(source = 'musiker', root = 'artist', model = musiker)
    mstmt = imus.save(bulk_create=True)
    print(mstmt)
    print("Musiker importiert.\n")
    m.Musiker = imus

    print("Importiere Musiker-Aliase...")
    imalias = MIZImporter(source='musiker', root = 'artist', model = musiker_alias)
    malstmt = imalias.save(bulk_create=True)
    print(malstmt)
    print("Musiker-Aliase importiert.\n")
    m.Alias = imalias
    
    print("Importiere Musiker-Genres...")
    imgenres = MIZImporter(source='rel_genreXartist', model=musiker.genre.through, distinct=True)
    imgenstmt = imgenres.save(bulk_create=True)
    print(imgenstmt)
    print("Musiker-Genres importiert.\n")
    m.Genres = imgenres
    #f.close()
    return m
    
def ImportBands(reset = False):
    b = namedtuple('Bands', ['Bands', 'Alias', 'Genres', 'Mitglieder', 'Zuweisung'])
    #f = open('ExportData/logs/ImportBands.txt')
    if reset:
        print("Lösche Bands...")
        band.objects.all().delete()
#        print("Lösche Band-Mitglieder...\n\n")
#        musiker

    
    print("Importiere Bands...")
    iband = MIZImporter(source = 'bands', root = 'artist', model = band)
    bstmt = iband.save(bulk_create=True)
    print(bstmt)
    print("Bands importiert.\n")
    b.Bands = iband

    print("Importiere Bands-Aliase...")
    ibalias = MIZImporter(source='bands', root = 'artist', model = band_alias)
    balstmt = ibalias.save(bulk_create=True)
    print(balstmt)
    print("Bands-Aliase importiert.\n")
    b.Alias = ibalias
    
    print("Importiere Bands-Genres...")
    ibgenres = MIZImporter(source='rel_genreXartist', model = band.genre.through,  distinct = True)
    bgenstmt = ibgenres.save(bulk_create=True)
    print(bgenstmt)
    print("Bands-Genres importiert.\n")
    b.Genres = ibgenres
    
    print("Importiere Band-Mitglieder...")
    ibmtgld = MIZImporter(source='bands', root='artist', model=musiker, distinct = True)
    ibmtgldstmt = ibmtgld.save(bulk_create=True)
    print(ibmtgldstmt)
    print("Band-Mitglieder importiert.\n")
    b.Mitglieder = ibmtgld
    
    print("Importiere Zuweisungen Band:Band-Mitglieder...")
    ibb = MIZImporter(source='bands', root='artist', model=band.mitglieder.through,  distinct = True)
    ibbstmt = ibb.save(bulk_create=True)
    print(ibbstmt)
    print("Zuweisungen importiert...")
    b.Zuweisung = ibb
    
    #f.close()
    return b

def Test():
    mp = MIZImporter(source='musiker', root='artist', model = person,  distinct = True)
    mm = MIZImporter(source='musiker', root='artist', model = musiker)
    return mp,  mm
    
