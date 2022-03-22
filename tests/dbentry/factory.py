import factory

from dbentry import models as _models
from tests.factory import MIZModelFactory, SubFactory, ISSNFaker, UniqueFaker


class AutorFactory(MIZModelFactory):
    class Meta:
        model = _models.Autor

    person = SubFactory('dbentry.factory.PersonFactory', required=True)

    # noinspection PyMethodParameters
    @factory.lazy_attribute
    def kuerzel(obj):
        """Prepare a 2 character token based on the Person's name."""
        if obj.person is None:
            return 'XY'
        # noinspection PyUnresolvedReferences
        vorname, nachname = obj.person.vorname, obj.person.nachname
        if vorname:
            return vorname[0] + nachname[0]
        return nachname[:2].upper()


class BandFactory(MIZModelFactory):
    class Meta:
        model = _models.Band
        django_get_or_create = ['band_name']

    band_name = factory.Faker('company')


class BundeslandFactory(MIZModelFactory):
    class Meta:
        model = _models.Bundesland
        django_get_or_create = ['bland_name', 'code']

    bland_name = factory.Faker('state')
    code = factory.Faker('state_abbr')


class GenreFactory(MIZModelFactory):
    class Meta:
        model = _models.Genre
        django_get_or_create = ['genre']


class LandFactory(MIZModelFactory):
    class Meta:
        model = _models.Land
        django_get_or_create = ['land_name', 'code']

    land_name = UniqueFaker('country')
    # land.code has unique=True and max_length of 4.
    # If we were to use a UniqueFaker that max_length might be exceeded
    # depending on the sequence counter (even with a faker that returns very
    # short strings such as 'country_code').
    # The end of land_name includes a unique sequence element, so just use the
    # last four chars of that name:
    code = factory.LazyAttribute(lambda o: o.land_name[-4:])


class MagazinFactory(MIZModelFactory):
    class Meta:
        model = _models.Magazin
        django_get_or_create = ['magazin_name']

    magazin_name = factory.Sequence(lambda n: 'TestMagazin' + str(n))
    issn = ISSNFaker()


class MonatFactory(MIZModelFactory):
    class Meta:
        model = _models.Monat
        django_get_or_create = ['monat', 'abk', 'ordinal']

    monat = factory.Faker('month_name')
    abk = factory.LazyAttribute(lambda o: o.monat[:3])
    ordinal = factory.Sequence(lambda n: n)


class MusikerFactory(MIZModelFactory):
    class Meta:
        model = _models.Musiker
        django_get_or_create = ['kuenstler_name']

    kuenstler_name = factory.Sequence(lambda n: 'TestMusiker' + str(n))


class OrtFactory(MIZModelFactory):
    class Meta:
        model = _models.Ort

    stadt = factory.Faker('city')


class PersonFactory(MIZModelFactory):
    class Meta:
        model = _models.Person

    vorname = factory.Faker('first_name')
    nachname = factory.Faker('last_name')


class SchlagwortFactory(MIZModelFactory):
    class Meta:
        model = _models.Schlagwort
        django_get_or_create = ['schlagwort']
