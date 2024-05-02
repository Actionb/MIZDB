import pytest

from dbentry import models as _models
from dbentry.export.factory import resource_factory
from tests.model_factory import make

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def person():
    return make(_models.Person, vorname="Alice", nachname="Testman")


@pytest.fixture
def urls():
    return (
        make(_models.MusikerURL, url="www.google.com"),
        make(_models.MusikerURL, url="www.duckduckgo.com"),
    )


@pytest.fixture
def genres():
    return (
        make(_models.Genre, genre="Blues"),
        make(_models.Genre, genre="Rock"),
    )


@pytest.fixture
def aliase():
    return (
        make(_models.MusikerAlias, alias="Bob"),
        make(_models.MusikerAlias, alias="Charlie"),
    )


@pytest.fixture
def bands():
    return (
        make(_models.Band, band_name="Alice's Band"),
        make(_models.Band, band_name="The Fancy Test Club"),
    )


@pytest.fixture
def orte():
    de = make(_models.Land, land_name="Deutschland", code="DE")
    return (
        make(_models.Ort, stadt="Alice Town", land=de),
        make(_models.Ort, stadt="Bob City", land=de),
    )


@pytest.fixture
def musiker(person, urls, genres, aliase, bands, orte):
    musiker = make(
        _models.Musiker,
        kuenstler_name="Alicia Testy",
        beschreibung="She tests stuff under a pseudonym",
        person=person,
    )
    musiker.urls.set(urls)
    musiker.genre.set(genres)
    musiker.musikeralias_set.set(aliase)  # noqa
    musiker.band_set.set(bands)  # noqa
    musiker.orte.set(orte)
    return musiker


@pytest.fixture
def resource():
    return resource_factory(_models.Musiker)()


@pytest.fixture
def dataset(musiker, resource):
    return resource.export(queryset=_models.Musiker.objects.filter(pk=musiker.pk))


@pytest.fixture
def datadict(dataset):
    return dataset.dict[0]


def sort(_list):
    return sorted(str(i) for i in _list)


def test_can_export(dataset):
    assert len(dataset) == 1


def test_headers(dataset):
    assert dataset.headers == [
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


def test_queryset_select_related(resource):
    export_queryset = resource.filter_export(resource.get_queryset())
    select_related = export_queryset.query.select_related
    assert select_related
    assert "person" in select_related


def test_musiker_data(datadict, musiker):
    assert datadict["Id"] == musiker.pk
    assert datadict["Künstlername"] == "Alicia Testy"


def test_person_data(datadict, person):
    assert datadict["Person"] == "Alice Testman"


def test_url_data(datadict, urls):
    assert datadict["Webseiten"] == ", ".join(str(i) for i in sort(urls))


def test_genre_data(datadict, genres):
    assert datadict["Genres"] == ", ".join(str(i) for i in sort(genres))


def test_alias_data(datadict, aliase):
    assert datadict["Alias"] == ", ".join(str(i) for i in sort(aliase))


def test_band_data(datadict, bands):
    assert datadict["Bands (Mitglied)"] == ", ".join(str(i) for i in sort(bands))


def test_ort_data(datadict, orte):
    assert datadict["Assoziierte Orte"] == "; ".join(str(i) for i in sort(orte))


def test_instrument_data(datadict):
    assert datadict["Instrumente"] == "-"
