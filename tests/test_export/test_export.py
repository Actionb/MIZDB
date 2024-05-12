from dbentry import models as _models
from dbentry.export.factory import resource_factory
from tests.case import MIZTestCase
from tests.model_factory import make


def sort(_list):
    return sorted(str(i) for i in _list)


class TestExport(MIZTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.person = person = make(_models.Person, vorname="Alice", nachname="Testman")
        cls.urls = urls = (
            make(_models.MusikerURL, url="www.google.com"),
            make(_models.MusikerURL, url="www.duckduckgo.com"),
        )
        cls.genres = genres = (
            make(_models.Genre, genre="Blues"),
            make(_models.Genre, genre="Rock"),
        )
        cls.aliase = aliase = (
            make(_models.MusikerAlias, alias="Bob"),
            make(_models.MusikerAlias, alias="Charlie"),
        )
        cls.bands = bands = (
            make(_models.Band, band_name="Alice's Band"),
            make(_models.Band, band_name="The Fancy Test Club"),
        )
        de = make(_models.Land, land_name="Deutschland", code="DE")
        cls.orte = orte = (
            make(_models.Ort, stadt="Alice Town", land=de),
            make(_models.Ort, stadt="Bob City", land=de),
        )
        cls.musiker = musiker = make(
            _models.Musiker,
            kuenstler_name="Alicia Testy",
            beschreibung="She tests stuff under a pseudonym",
            person=person,
        )
        musiker.urls.set(urls)  # noqa
        musiker.genre.set(genres)
        musiker.musikeralias_set.set(aliase)  # noqa
        musiker.band_set.set(bands)
        musiker.orte.set(orte)

    def setUp(self):
        super().setUp()
        self.resource = resource_factory(_models.Musiker)()

    def get_dataset(self):
        return self.resource.export(queryset=_models.Musiker.objects.filter(pk=self.musiker.pk))

    def get_datadict(self):
        return self.get_dataset().dict[0]

    def test_can_export(self):
        dataset = self.get_dataset()
        self.assertEqual(len(dataset), 1)

    def test_export_headers(self):
        expected = [
            "Id",
            "Künstlername",
            "Person",
            "Webseiten",
            "Genres",
            "Alias",
            "Bands (Mitglied)",
            "Assoziierte Orte",
            "Instrumente",
            "Beschreibung",
        ]
        dataset = self.get_dataset()
        self.assertEqual(dataset.headers, expected)

    def test_queryset_select_related(self):
        export_queryset = self.resource.filter_export(self.resource.get_queryset())
        self.assertIn("person", export_queryset.query.select_related)

    def test_musiker_Data(self):
        datadict = self.get_datadict()
        self.assertEqual(datadict["Id"], self.musiker.pk)
        self.assertEqual(datadict["Künstlername"], "Alicia Testy")

    def test_person_data(self):
        datadict = self.get_datadict()
        self.assertEqual(datadict["Person"], "Alice Testman")

    def test_url_data(self):
        datadict = self.get_datadict()
        self.assertEqual(datadict["Webseiten"], ", ".join(sort(self.urls)))

    def test_genre_data(self):
        datadict = self.get_datadict()
        self.assertEqual(datadict["Genres"], ", ".join(sort(self.genres)))

    def test_alias_data(self):
        datadict = self.get_datadict()
        self.assertEqual(datadict["Alias"], ", ".join(sort(self.aliase)))

    def test_band_data(self):
        datadict = self.get_datadict()
        self.assertEqual(datadict["Bands (Mitglied)"], ", ".join(sort(self.bands)))

    def test_ort_data(self):
        datadict = self.get_datadict()
        self.assertEqual(datadict["Assoziierte Orte"], "; ".join(sort(self.orte)))

    def test_instrument_data(self):
        datadict = self.get_datadict()
        self.assertEqual(datadict["Instrumente"], "-")
