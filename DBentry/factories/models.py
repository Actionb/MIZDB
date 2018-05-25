from . import *
from DBentry.models import *

class ArtikelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = artikel
    schlagzeile = factory.Faker('sentence')
    seite = random.randrange(32766)

    ausgabe = factory.SubFactory('DBentry.factories.models.AusgabeFactory')

class AudioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = audio
    titel = factory.Faker('word')

class AusgabeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ausgabe
    magazin = factory.SubFactory('DBentry.factories.models.MagazinFactory')

class AusgabeJahrFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ausgabe_jahr
    jahr = random.randrange(1900, 2017)

    ausgabe = factory.SubFactory('DBentry.factories.models.AusgabeFactory')

class AusgabeLnumFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ausgabe_lnum
    lnum = random.randrange(32766)

    ausgabe = factory.SubFactory('DBentry.factories.models.AusgabeFactory')

class AusgabeMonatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ausgabe_monat
    ausgabe = factory.SubFactory('DBentry.factories.models.AusgabeFactory')
    monat = factory.SubFactory('DBentry.factories.models.MonatFactory')

class AusgabeNumFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ausgabe_num
    num = random.randrange(32766)

    ausgabe = factory.SubFactory('DBentry.factories.models.AusgabeFactory')

class AutorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = autor
    person = factory.SubFactory('DBentry.factories.models.PersonFactory') 
    kuerzel = factory.Faker('word')
    
class BandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = band
    band_name = factory.Faker('word')

class BandAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = band_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.BandFactory')

class BestandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = bestand
    lagerort = factory.SubFactory('DBentry.factories.models.LagerortFactory')

class BildmaterialFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = bildmaterial
    titel = factory.Faker('word')

class BuchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = buch
    titel = factory.Faker('word')
    
    genre = M2MDeclaration('genre')

class BundeslandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = bundesland
    bland_name = factory.Faker('word') #TODO: alternative
    code = factory.Faker('word')

    land = factory.SubFactory('DBentry.factories.models.LandFactory')

class DateiFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = datei
    titel = factory.Faker('word')

class DokumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = dokument
    titel = factory.Faker('word')

#class FavoritenFactory(factory.django.DjangoModelFactory):
#    class Meta:
#        model = Favoriten
#    user = factory.SubFactory('DBentry.factories.models.UserFactory')

class FormatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Format
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    format_typ = factory.SubFactory('DBentry.factories.models.FormattypFactory')

class FormatsizeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FormatSize
    size = factory.Faker('word')

class FormattagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FormatTag
    tag = factory.Faker('word')

class FormattypFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FormatTyp
    typ = factory.Faker('word')

class GeberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = geber
    name = factory.Faker('name')
    
class GenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = genre
    genre = factory.Sequence(lambda n: 'TestGenre-' + str(n))

class GenreAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = genre_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.GenreFactory')

class HerausgeberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Herausgeber
class InstrumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = instrument
    instrument = factory.Sequence(lambda n: 'Testinstrument-' + str(n))
    kuerzel = factory.LazyAttribute(lambda o: o.instrument[:2])

class InstrumentAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = instrument_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.InstrumentFactory')

class KreisFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = kreis
    name = factory.Faker('word')

    bland = factory.SubFactory('DBentry.factories.models.BundeslandFactory')

class LagerortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = lagerort
    ort = factory.Faker('word')

class LandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = land
    land_name = factory.Sequence(lambda n: 'TestLand-' + str(n))
    code = factory.Sequence(lambda n: 'Testcode-' + str(n))

class LandAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = land_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.LandFactory')

class MagazinFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = magazin
    magazin_name = factory.Faker('word')

class MemorabilienFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = memorabilien
    titel = factory.Faker('word')

class MonatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = monat
    monat = factory.Faker('month_name')
    abk = factory.LazyAttribute(lambda o: o.monat[:3])
    ordinal = random.randrange(1, 13)

class MusikerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = musiker
    kuenstler_name = factory.Faker('name')

class MusikerAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = musiker_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.MusikerFactory')

class NoiseredFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NoiseRed
    verfahren = factory.Faker('word')

class OrganisationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organisation
    name = factory.Faker('word')

class OrtFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ort
    stadt = factory.Faker('city')
    bundesland = factory.SubFactory('DBentry.factories.models.BundeslandFactory')
    land = factory.SubFactory('DBentry.factories.models.LandFactory')

class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = person
    vorname = factory.Faker('first_name')
    nachname = factory.Faker('last_name')

class PlattenfirmaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = plattenfirma
    name = factory.Faker('word')

class ProvenienzFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = provenienz
    geber = factory.SubFactory('DBentry.factories.models.GeberFactory')

class SchlagwortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = schlagwort
    schlagwort = factory.Sequence(lambda n: 'Testschlagwort-' + str(n))

class SchlagwortAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = schlagwort_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.SchlagwortFactory')

class SchriftenreiheFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = schriftenreihe
    name = factory.Faker('word')

class SenderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = sender
    name = factory.Faker('word')

class SenderAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = sender_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.SenderFactory')

class SpielortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = spielort
    name = factory.Faker('word')

    ort = factory.SubFactory('DBentry.factories.models.OrtFactory')

class SpielortAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = spielort_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.SpielortFactory')

class SpracheFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = sprache
    sprache = factory.Faker('word')
    abk = factory.Faker('word')

class TechnikFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = technik
    titel = factory.Faker('word')

class VeranstaltungFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = veranstaltung
    name = factory.Faker('word')
    datum = factory.Faker('date')

    spielort = factory.SubFactory('DBentry.factories.models.SpielortFactory')

class VeranstaltungAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = veranstaltung_alias
    alias = factory.Faker('word')

    parent = factory.SubFactory('DBentry.factories.models.VeranstaltungFactory')

class VerlagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = verlag
    verlag_name = factory.Faker('word')

class VideoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = video
    titel = factory.Faker('word')
    tracks = random.randrange(32766)
    laufzeit = factory.Faker('time')

