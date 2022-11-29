from collections import OrderedDict

from dbentry import models as _models
from dbentry.utils.serialize import RelatedStringSerializer, get_documents
from tests.case import DataTestCase
from tests.model_factory import make
from tests.test_utils.models import Audio, Band, Bestand, Genre, Musiker


class TestSerializer(DataTestCase):
    model = _models.Audio

    @classmethod
    def setUpTestData(cls):
        musiker1 = make(Musiker, kuenstler_name='John Lennon')
        musiker2 = make(Musiker, kuenstler_name='Paul McCartney')
        cls.audio = make(Audio, musiker=[musiker1, musiker2])

    def test_handle_m2m_field(self):
        """
        Assert that for m2m relations the string representations of the
        related objects are returned rather than their pks.
        """
        serialized = RelatedStringSerializer().serialize([self.audio])
        self.assertEqual(len(serialized), 1)
        doc = serialized[0]
        self.assertIn('musiker', doc['fields'])
        self.assertEqual(doc['fields']['musiker'], 'John Lennon, Paul McCartney')

    def test_handle_fk_field(self):
        """
        Assert that for FK relations the string representation of the related
        object is returned rather than its pk.
        """
        b = make(Bestand, audio=self.audio)
        serialized = RelatedStringSerializer().serialize([b])
        self.assertEqual(len(serialized), 1)
        doc = serialized[0]
        self.assertIn('audio', doc['fields'])
        self.assertEqual(doc['fields']['audio'], str(self.audio))


class TestDocuments(DataTestCase):
    model = Audio

    @classmethod
    def setUpTestData(cls):
        cls.genre1 = make(Genre, genre='Rock')
        cls.genre2 = make(Genre, genre='Beat')
        cls.musiker1 = make(Musiker, kuenstler_name='John Lennon')
        cls.musiker2 = make(Musiker, kuenstler_name='Paul McCartney')
        cls.band1 = make(Band, band_name='The Beatles')
        cls.audio = make(
            Audio,
            titel='The White Album',
            tracks=30,
            beschreibung='Das neunte Studioalbum der Beatles.',
            bemerkungen='Kratzer auf der B-Seite.',
            musiker=[cls.musiker1, cls.musiker2],
            band=[cls.band1],
            genre=[cls.genre1, cls.genre2],
        )

    def test_get_documents(self):
        """Assert that get_documents returns the expected dictionary."""
        fields = ['titel', 'tracks', 'beschreibung', 'bemerkungen', 'musiker', 'band', 'genre']
        docs = list(get_documents(self.model.objects.all(), fields=fields))
        self.assertEqual(len(docs), 1)

        expected = OrderedDict({
            'Objekt': self.model._meta.verbose_name,
            'ID': self.audio.pk,
            'Titel': 'The White Album',
            'Anz. Tracks': 30,
            'Beschreibung': 'Das neunte Studioalbum der Beatles.',
            'Bemerkungen': 'Kratzer auf der B-Seite.',
            'Musiker': 'John Lennon, Paul McCartney',
            'Bands': 'The Beatles',
            'Genres': 'Rock, Beat',
        })
        # comparing lists gives better info on failure
        self.assertEqual(list(docs[0].keys()), list(expected.keys()))
        doc = docs[0].items().__iter__()
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

    def test_get_documents_fields(self):
        """
        Assert that get_documents only returns values for fields specified in
        the 'fields' argument.
        """
        docs = list(get_documents(self.model.objects.all(), fields=('titel',)))
        self.assertEqual(len(docs), 1)
        self.assertEqual(tuple(docs[0].keys()), ('Objekt', 'ID', 'Titel'))

    def test_get_documents_remove_empty(self):
        """Assert that get_documents excludes 'empty' values if 'remove_empty' argument is True."""
        self.audio.beschreibung = ''
        self.audio.save()
        docs = list(get_documents(self.model.objects.all(), fields=('titel', 'beschreibung')))
        self.assertEqual(len(docs), 1)
        self.assertNotIn('Beschreibung', docs[0].keys())
