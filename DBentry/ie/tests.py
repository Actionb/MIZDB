
FILE_NAME = '/home/philip/DB/Discogs Export/miz-ruhr2-collection-20170731-0402.csv'
FILE_NAME_WIN = 'ImportData/miz-ruhr2.csv'

from DBentry.models import *

def test_reader(model = audio):
    return DiscogsReader(model, open('/home/philip/DB/Discogs Export/miz-ruhr2-collection-20170731-0402.csv'))

def test_muba():
    d = [i['Artist'] for i in DiscogsReader().read()]
    return split_MuBa(d)

from .again import *

relations = [Format.audio.field.rel, Format.tag.rel, Format.format_typ.field.rel, Format.format_size.field.rel, 
            audio.musiker.rel, audio.band.rel, audio.plattenfirma.rel
]


def test():
    s = Stuff([audio.band.field.rel])
    s.mcs[audio].data = [{'titel':'MC Test', 'release_id':[1]}, {'titel':'MC Test Nr 2', 'release_id':[2]}]
    s.mcs[band].data = [{'band_name':'MC TestBand', 'release_id' : [1, 2]}, {'band_name':'MC TestBand 2', 'release_id':[1]}]
    
    return s

mb_importer = DiscogsImporter([musiker, band], file_path=FILE_NAME)

def test_importer():
    i = DiscogsImporter([musiker,band],file_path=FILE_NAME)
    c = i.cleaned_data
    james = [d for d in c[musiker] if d['kuenstler_name']=='James Last']

    return i, c, james
    
def test_relation():
    r = RelationImport([audio.band.rel, audio.musiker.rel], file=open(FILE_NAME))
    return r
    
def test_relation_import():
    file = open('/home/philip/DB/Discogs Export/TestStuff.csv')
    relations = [Format.audio.field.rel, Format.tag.rel, Format.format_typ.field.rel, Format.format_size.field.rel, audio.plattenfirma.rel]
    relations += [audio.band.rel, audio.musiker.rel]
    r = RelationImport(relations, file=file)
    return r
