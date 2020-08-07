import DBentry.m2m as _m2m

from DBentry.tests.base import DataTestCase


class TestM2mAudioAusgabe(DataTestCase):

    model = _m2m.m2m_audio_ausgabe
    raw_data = [{'ausgabe__e_datum': '2020-05-05'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), '2020-05-05')


class TestM2mAudioBand(DataTestCase):

    model = _m2m.m2m_audio_band
    raw_data = [{'band__band_name': 'The Beep Boops'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'The Beep Boops')


class TestM2mAudioGenre(DataTestCase):

    model = _m2m.m2m_audio_genre
    raw_data = [{'genre__genre': 'Jazz'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Jazz')


class TestM2mAudioMusiker(DataTestCase):

    model = _m2m.m2m_audio_musiker
    raw_data = [{'musiker__kuenstler_name': 'Beep'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep')


class TestM2mAudioOrt(DataTestCase):

    model = _m2m.m2m_audio_ort
    raw_data = [{'ort__stadt': 'Beep', 'ort__land__land_name': 'Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep, Boop')


class TestM2mAudioPerson(DataTestCase):

    model = _m2m.m2m_audio_person
    raw_data = [{'person__vorname': 'Beep', 'person__nachname': 'Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')


class TestM2mAudioPlattenfirma(DataTestCase):

    model = _m2m.m2m_audio_plattenfirma
    raw_data = [{'plattenfirma__name': 'Beep Boop Records'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop Records')


class TestM2mAudioSchlagwort(DataTestCase):

    model = _m2m.m2m_audio_schlagwort
    raw_data = [{'schlagwort__schlagwort': 'Beeping'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beeping')


class TestM2mAudioSpielort(DataTestCase):

    model = _m2m.m2m_audio_spielort
    raw_data = [{'spielort__name': 'Beep Club'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Club')

class TestM2mAudioVeranstaltung(DataTestCase):

    model = _m2m.m2m_audio_veranstaltung
    raw_data = [{'veranstaltung__name': 'Boop Fest', 'veranstaltung__datum': '2020-05-05'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Boop Fest (05 Mai 2020)')


class TestM2mArtikelAutor(DataTestCase):

    model = _m2m.m2m_artikel_autor
    raw_data = [{'autor__person__vorname': 'Beep', 'autor__person__nachname': 'Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop (BB)')


class TestM2mArtikelBand(DataTestCase):

    model = _m2m.m2m_artikel_band
    raw_data = [{'band__band_name': 'The Beep Boops'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'The Beep Boops')


class TestM2mArtikelGenre(DataTestCase):

    model = _m2m.m2m_artikel_genre
    raw_data = [{'genre__genre': 'Beep'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep')


class TestM2mArtikelMusiker(DataTestCase):

    model = _m2m.m2m_artikel_musiker
    raw_data = [{'musiker__kuenstler_name': 'Beep Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')


class TestM2mArtikelOrt(DataTestCase):

    model = _m2m.m2m_artikel_ort
    raw_data = [{'ort__stadt': 'Beep', 'ort__land__land_name': 'Boop'
    }]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep, Boop')


class TestM2mArtikelPerson(DataTestCase):

    model = _m2m.m2m_artikel_person
    raw_data = [{'person__vorname': 'Beep', 'person__nachname': 'Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')


class TestM2mArtikelSchlagwort(DataTestCase):

    model = _m2m.m2m_artikel_schlagwort
    raw_data = [{'schlagwort__schlagwort': 'Beeping'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beeping')


class TestM2mArtikelSpielort(DataTestCase):

    model = _m2m.m2m_artikel_spielort
    raw_data = [{'spielort__name': 'Beep Club'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Club')


class TestM2mArtikelVeranstaltung(DataTestCase):

    model = _m2m.m2m_artikel_veranstaltung
    raw_data = [{'veranstaltung__name': 'Boop Fest', 'veranstaltung__datum': '2020-05-05'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Boop Fest (05 Mai 2020)')


class TestM2mBandGenre(DataTestCase):

    model = _m2m.m2m_band_genre
    raw_data = [{'genre__genre': 'Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Boop')


class TestM2mBandMusiker(DataTestCase):

    model = _m2m.m2m_band_musiker
    raw_data = [{'musiker__kuenstler_name': 'Beep Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')


class TestM2mAutorMagazin(DataTestCase):

    model = _m2m.m2m_autor_magazin
    raw_data = [{'magazin__magazin_name': 'Beep Boop Magazine'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop Magazine')


class TestM2mMagazinGenre(DataTestCase):

    model = _m2m.m2m_magazin_genre
    raw_data = [{'genre__genre': 'Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Boop')


class TestM2mMagazinVerlag(DataTestCase):

    model = _m2m.m2m_magazin_verlag
    raw_data = [{'verlag__verlag_name': 'Beep Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')


class TestM2mMagazinHerausgeber(DataTestCase):

    model = _m2m.m2m_magazin_herausgeber
    raw_data = [{'herausgeber__herausgeber': 'Beep Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')


class TestM2mMusikerGenre(DataTestCase):

    model = _m2m.m2m_musiker_genre
    raw_data = [{'genre__genre': 'Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Boop')


class TestM2mMusikerInstrument(DataTestCase):

    model = _m2m.m2m_musiker_instrument
    raw_data = [{'instrument__instrument': 'Beep', 'instrument__kuerzel': 'bo'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep (bo)')


class TestM2mVideoMusiker(DataTestCase):

    model = _m2m.m2m_video_musiker
    raw_data = [{'musiker__kuenstler_name': 'Beep Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')


class TestM2mDateiMusiker(DataTestCase):

    model = _m2m.m2m_datei_musiker
    raw_data = [{'musiker__kuenstler_name': 'Beep Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')
