
FILE_NAME = '/home/philip/DB/Discogs Export/miz-ruhr2-collection-20170731-0402.csv'
FILE_NAME_WIN = 'ImportData/miz-ruhr2.csv'


def test_reader(model = audio):
    return DiscogsReader(model, open('/home/philip/DB/Discogs Export/miz-ruhr2-collection-20170731-0402.csv'))

def test_muba():
    d = [i['Artist'] for i in DiscogsReader().read()]
    return split_MuBa(d)
