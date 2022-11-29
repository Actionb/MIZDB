from collections import OrderedDict

from django.db.models import QuerySet
from django.test import TestCase

from dbentry import models as _models
from dbentry.utils.document import ArtikelDocument, get_documents
from tests.case import DataTestCase
from tests.model_factory import make


class TestDocument(DataTestCase):

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
            ausgabe=cls.ausgabe,
            musiker=[cls.musiker1, cls.musiker2],
            band=[cls.band1],
            genre=[cls.genre1, cls.genre2]
        )
        super().setUpTestData()

    def test(self):
        fields = [
            'ausgabe', 'schlagzeile', 'seite', 'beschreibung',
            'musiker', 'band', 'genre'
        ]
        documents = list(get_documents(self.model.objects.filter(pk=self.artikel.pk)))
        self.assertEqual(len(documents), 1)

        expected = OrderedDict({
            'Objekt': 'Artikel',
            'ID': self.artikel.pk,
            'Ausgabe': f'{self.ausgabe} ({self.mag})',
            'Schlagzeile': 'Die Dokumentenansicht funktioniert!',
            'Seite': '20f',
            'Beschreibung': '',
            'Musiker': 'John Lennon, Paul McCartney',
            'Bands': 'The Beatles',
            'Genres': 'Beat, Rock',
        })
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

