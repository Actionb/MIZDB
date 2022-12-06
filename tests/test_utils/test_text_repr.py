from collections import OrderedDict

from dbentry import models as _models
from dbentry.utils.text_repr import get_text_representations, registry
from tests.case import DataTestCase
from tests.model_factory import make


class TestTextRepr(DataTestCase):
    model = _models.Artikel

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.ausgabe = make(_models.Ausgabe, magazin=cls.mag)
        cls.musiker1 = make(_models.Musiker, kuenstler_name='John Lennon')
        cls.musiker2 = make(_models.Musiker, kuenstler_name='Paul McCartney')
        cls.band1 = make(_models.Band, band_name='The Beatles')
        cls.genre1 = make(_models.Genre, genre='Rock')
        cls.genre2 = make(_models.Genre, genre='Beat')
        cls.artikel = make(
            _models.Artikel,
            schlagzeile='Die Dokumentenansicht funktioniert!',
            seite=20,
            seitenumfang='f',
            zusammenfassung='Dieser Artikel existiert für Tests.',
            ausgabe=cls.ausgabe,
            musiker=[cls.musiker1, cls.musiker2],
            band=[cls.band1],
            genre=[cls.genre1, cls.genre2]
            # TODO: add Veranstaltung
        )
        super().setUpTestData()

    def test(self):
        documents = list(
            get_text_representations(self.model.objects.filter(pk=self.artikel.pk))
        )
        self.assertEqual(len(documents), 1)

        expected = OrderedDict(
            {
                'Objekt': 'Artikel',
                'ID': self.artikel.pk,
                'Ausgabe': f'{self.ausgabe} ({self.mag})',
                'Schlagzeile': 'Die Dokumentenansicht funktioniert!',
                'Seite': '20f',
                'Zusammenfassung': 'Dieser Artikel existiert für Tests.',
                'Beschreibung': '',
                'Autoren': '',
                'Musiker': 'John Lennon; Paul McCartney',
                'Bands': 'The Beatles',
                'Schlagwörter': '',
                'Genres': 'Beat; Rock',
                'Orte': '',
                'Spielorte': '',
                'Veranstaltungen': '',
                'Personen': '',
            }
        )
        self.assertEqual(list(documents[0].keys()), list(expected.keys()))
        doc = documents[0].items().__iter__()
        exp = expected.items().__iter__()
        i = 0
        while True:
            try:
                doc_k, doc_v = next(doc)
                exp_k, exp_v = next(exp)
                with self.subTest(key=doc_k, i=i):
                    self.assertEqual(doc_k, exp_k)
                    self.assertEqual(doc_v, exp_v)
            except StopIteration:
                break
            i += 1


class ParserTestCase(DataTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model)
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.parser = registry[self.model]()
        self.queryset = self.parser.modify_queryset(self.queryset)


class TestPersonParser(ParserTestCase):
    model = _models.Person

    def test_get_annotations(self):
        expected = ['autor_list', 'musiker_list', 'ort_list', 'url_list']
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID', 'Vorname', 'Nachname', 'Normdatei ID', 'Normdatei Name',
            'Link DNB', 'Beschreibung', 'Webseiten', 'Musiker', 'Autoren', 'Orte'
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestMusikerParser(ParserTestCase):
    model = _models.Musiker

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_get_annotations(self):
        expected = [
            'band_list', 'genre_list', 'instrument_list', 'alias_list',
            'ort_list', 'url_list'
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Künstlername',
            'Beschreibung',
            'Person',
            'Bands',
            'Aliases',
            'Webseiten',
            'Genres',
            'Instrumente',
            'Orte',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestBandParser(ParserTestCase):
    model = _models.Band

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'genre_list', 'alias_list', 'ort_list', 'url_list'
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Bandname',
            'Beschreibung',
            'Musiker',
            'Aliases',
            'Webseiten',
            'Genres',
            'Orte',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestAutorParser(ParserTestCase):
    model = _models.Autor

    def test_get_annotations(self):
        expected = ['magazin_list', 'url_list']
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = ['Objekt', 'ID', 'Name', 'Kürzel', 'Webseiten', 'Magazine']
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestAusgabeParser(ParserTestCase):
    model = _models.Ausgabe

    def test_get_annotations(self):
        expected = [
            'jahre_list', 'num_list', 'lnum_list', 'monat_list',
            'audio_list', 'video_list', 'bestand_list'
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Magazine',
            'Name',
            'Bearbeitungsstatus',
            'Ist Sonderausgabe',
            'Beschreibung',
            'Erscheinungsdatum',
            'Jahrgang',
            'Jahre', 'Nummern', 'lfd. Nummern', 'Monate',
            'Audio-Materialien', 'Video-Materialien', 'Bestände'
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestMagazinParser(ParserTestCase):
    model = _models.Magazin

    def test_get_annotations(self):
        expected = [
            'url_list', 'genre_list', 'verlag_list', 'herausgeber_list', 'ort_list'
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID', 'Name', 'Ist Fanzine', 'ISSN', 'Beschreibung',
            'Webseiten', 'Genres', 'Verlage', 'Herausgeber', 'Orte'
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestArtikelParser(ParserTestCase):
    model = _models.Artikel

    def test_get_annotations(self):
        expected = [
            'autor_list', 'musiker_list', 'band_list',
            'genre_list', 'schlagwort_list',
            'ort_list', 'spielort_list',
            'person_list'
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Ausgabe',
            'Schlagzeile',
            'Seite',
            'Zusammenfassung',
            'Beschreibung',
            'Autoren',
            'Musiker', 'Bands',
            'Schlagwörter', 'Genres',
            'Orte', 'Spielorte', 'Veranstaltungen',
            'Personen',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestBuchParser(ParserTestCase):
    model = _models.Buch

    def test_get_annotations(self):
        expected = [
            'autor_list', 'musiker_list', 'band_list',
            'genre_list', 'schlagwort_list',
            'ort_list', 'spielort_list',
            'person_list', 'herausgeber_list', 'verlag_list',
            'bestand_list'
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel', 'Titel (Original)',
             'Seitenumfang',
            'Jahr', 'Jahr (Original)',
            'Auflage',
            'Schriftenreihe',
            'Sammelband', 'Ist Sammelband',
            'ISBN', 'EAN',
            'Sprache',
            'Beschreibung',
            'Autoren', 'Musiker', 'Bands',
            'Schlagwörter', 'Genres',
            'Orte', 'Spielorte', 'Veranstaltungen',
            'Herausgeber', 'Verlage',
            'Bestände'
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestAudioParser(ParserTestCase):
    model = _models.Audio

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'band_list', 'autor_list',
            'schlagwort_list', 'genre_list',
            'ort_list', 'spielort_list', 'veranstaltung_list',
            'person_list', 'plattenfirma_list'
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Anz. Tracks',
            'Laufzeit',
            'Jahr',
            'Land',
            'Quelle',
            'Originalmaterial',
            'Plattennummer',
            'Release ID (discogs)',
            'Link discogs.com',
            'Beschreibung',
            'Speichermedium',
            'Musiker', 'Bands',
            'Schlagwörter', 'Genres',
            'Orte', 'Spielorte', 'Veranstaltungen',
            'Personen',
            'Plattenfirmen',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestPlakatParser(ParserTestCase):
    model = _models.Plakat

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'band_list',
            'schlagwort_list', 'genre_list',
            'ort_list', 'spielort_list', 'veranstaltung_list',
            'person_list',
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Signatur',
            'Größe',
            'Zeitangabe',
            'Beschreibung',
            'Bildreihe',
            'Schlagwörter', 'Genres',
            'Musiker', 'Band',
            'Orte', 'Spielorte', 'Veranstaltungen',
            'Person'
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestDokumentParser(ParserTestCase):
    model = _models.Dokument

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'band_list',
            'schlagwort_list', 'genre_list',
            'ort_list', 'spielort_list', 'veranstaltung_list',
            'person_list',
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Beschreibung',
            'Genres', 'Schlagwörter',
            'Personen', 'Band', 'Musiker',
            'Orte', 'Spielorte', 'Veranstaltungen',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestMemorabilienParser(ParserTestCase):
    model = _models.Memorabilien

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'band_list',
            'schlagwort_list', 'genre_list',
            'ort_list', 'spielort_list', 'veranstaltung_list',
            'person_list',
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Beschreibung',
            'Genres', 'Schlagwörter',
            'Personen', 'Band', 'Musiker',
            'Orte', 'Spielorte', 'Veranstaltungen',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestTechnikParser(ParserTestCase):
    model = _models.Technik

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'band_list',
            'schlagwort_list', 'genre_list',
            'ort_list', 'spielort_list', 'veranstaltung_list',
            'person_list',
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Beschreibung',
            'Genres', 'Schlagwörter',
            'Personen', 'Band', 'Musiker',
            'Orte', 'Spielorte', 'Veranstaltungen',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestVideoParser(ParserTestCase):
    model = _models.Video

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'band_list',
            'schlagwort_list', 'genre_list',
            'ort_list', 'spielort_list', 'veranstaltung_list',
            'person_list',
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Laufzeit',
            'Quelle',
            'Ist Originalmaterial',
            'Release ID', 'Link discogs.com',
            'Medium',
            'Beschreibung',
            'Musiker', 'Band',
            'Schlagwörter', 'Genres',
            'Orte', 'Spielorte', 'Veranstaltungen',
            'Personen',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestBestandParser(ParserTestCase):
    model = _models.Bestand

    def test_get_annotations(self):
        expected = [

        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [

        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestDateiParser(ParserTestCase):
    model = _models.Datei

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'band_list',
            'schlagwort_list', 'genre_list',
            'ort_list', 'spielort_list', 'veranstaltung_list',
            'person_list',
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Media Typ',
            'Datei',
            'Datei-Pfad',
            'Beschreibung',
            'Provenienz',
            'Genres', 'Schlagwörter',
            'Personen', 'Band', 'Musiker',
            'Orte', 'Spielorte', 'Veranstaltungen',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestBrochureParser(ParserTestCase):
    model = _models.Brochure

    def test_get_annotations(self):
        expected = ['genre_list', 'schlagwort_list', 'url_list']
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Art d. Kataloges',
            'Zusammenfassung',
            'Jahre',
            'Ausgabe',
            'Beschreibung',
            'Webseiten',
            'Genres',
            'Schlagwörter',
            'Bestände',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestKalenderParser(ParserTestCase):
    model = _models.Kalender

    def test_get_annotations(self):
        expected = ['genre_list', 'spielort_list', 'veranstaltung_list', 'url_list']
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Art d. Kataloges',
            'Zusammenfassung',
            'Jahre',
            'Ausgabe',
            'Beschreibung',
            'Webseiten',
            'Genres',
            'Spielorte', 'Veranstaltungen',
            'Bestände',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestKatalogParser(ParserTestCase):
    model = _models.Katalog

    def test_get_annotations(self):
        expected = ['genre_list', 'url_list']
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Art d. Kataloges',
            'Zusammenfassung',
            'Jahre',
            'Ausgabe',
            'Beschreibung',
            'Webseiten',
            'Genres',
            'Bestände',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)


class TestFotoParser(ParserTestCase):
    model = _models.Foto

    def test_get_annotations(self):
        expected = [
            'musiker_list', 'band_list',
            'schlagwort_list', 'genre_list',
            'ort_list', 'spielort_list', 'veranstaltung_list',
            'person_list',
        ]
        annotations = self.parser.get_annotations()
        self.assertCountEqual(list(annotations.keys()), expected)

    def test_get_text_repr(self):
        expected = [
            'Objekt', 'ID',
            'Titel',
            'Größe',
            'Zeitangabe',
            'Reihe',
            'Art des Fotos',
            'Ist Farbfoto',
            'Rechteinhaber',
            'Beschreibung',
            'Schlagwörter', 'Genres',
            'Band', 'Musiker',
            'Orte', 'Spielorte', 'Veranstaltungen',
            'Personen',
        ]
        text_repr = self.parser.get_text_repr(self.queryset.get())
        self.assertEqual(list(text_repr.keys()), expected)
