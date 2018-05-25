from . import *
from DBentry.m2m import *

class ArtikelAutorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_autor
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    autor = factory.SubFactory('DBentry.factories.models.AutorFactory')

class ArtikelBandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_band
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    band = factory.SubFactory('DBentry.factories.models.BandFactory')

class ArtikelGenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_genre
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    genre = factory.SubFactory('DBentry.factories.models.GenreFactory')

class ArtikelMusikerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_musiker
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    musiker = factory.SubFactory('DBentry.factories.models.MusikerFactory')

class ArtikelOrtFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_ort
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    ort = factory.SubFactory('DBentry.factories.models.OrtFactory')

class ArtikelPersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_person
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    person = factory.SubFactory('DBentry.factories.models.PersonFactory')

class ArtikelSchlagwortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_schlagwort
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    schlagwort = factory.SubFactory('DBentry.factories.models.SchlagwortFactory')

class ArtikelSpielortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_spielort
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    spielort = factory.SubFactory('DBentry.factories.models.SpielortFactory')

class ArtikelVeranstaltungFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_artikel_veranstaltung
    artikel = factory.SubFactory('DBentry.factories.models.ArtikelFactory')
    veranstaltung = factory.SubFactory('DBentry.factories.models.VeranstaltungFactory')

class AudioAusgabeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_ausgabe
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    ausgabe = factory.SubFactory('DBentry.factories.models.AusgabeFactory')

class AudioBandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_band
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    band = factory.SubFactory('DBentry.factories.models.BandFactory')

class AudioGenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_genre
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    genre = factory.SubFactory('DBentry.factories.models.GenreFactory')

class AudioMusikerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_musiker
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    musiker = factory.SubFactory('DBentry.factories.models.MusikerFactory')

class AudioOrtFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_ort
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    ort = factory.SubFactory('DBentry.factories.models.OrtFactory')

class AudioPersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_person
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    person = factory.SubFactory('DBentry.factories.models.PersonFactory')

class AudioPlattenfirmaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_plattenfirma
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    plattenfirma = factory.SubFactory('DBentry.factories.models.PlattenfirmaFactory')

class AudioSchlagwortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_schlagwort
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    schlagwort = factory.SubFactory('DBentry.factories.models.SchlagwortFactory')

class AudioSpielortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_spielort
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    spielort = factory.SubFactory('DBentry.factories.models.SpielortFactory')

class AudioVeranstaltungFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_audio_veranstaltung
    audio = factory.SubFactory('DBentry.factories.models.AudioFactory')
    veranstaltung = factory.SubFactory('DBentry.factories.models.VeranstaltungFactory')

class AutorMagazinFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_autor_magazin
    autor = factory.SubFactory('DBentry.factories.models.AutorFactory')
    magazin = factory.SubFactory('DBentry.factories.models.MagazinFactory')

class BandGenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_band_genre
    band = factory.SubFactory('DBentry.factories.models.BandFactory')
    genre = factory.SubFactory('DBentry.factories.models.GenreFactory')

class BandMusikerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_band_musiker
    band = factory.SubFactory('DBentry.factories.models.BandFactory')
    musiker = factory.SubFactory('DBentry.factories.models.MusikerFactory')

class DateiMusikerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_datei_musiker
    datei = factory.SubFactory('DBentry.factories.models.DateiFactory')
    musiker = factory.SubFactory('DBentry.factories.models.MusikerFactory')

class DateiQuelleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_datei_quelle
    datei = factory.SubFactory('DBentry.factories.models.DateiFactory')

class MagazinGenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_magazin_genre
    magazin = factory.SubFactory('DBentry.factories.models.MagazinFactory')
    genre = factory.SubFactory('DBentry.factories.models.GenreFactory')

class MusikerGenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_musiker_genre
    musiker = factory.SubFactory('DBentry.factories.models.MusikerFactory')
    genre = factory.SubFactory('DBentry.factories.models.GenreFactory')

class MusikerInstrumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_musiker_instrument
    musiker = factory.SubFactory('DBentry.factories.models.MusikerFactory')
    instrument = factory.SubFactory('DBentry.factories.models.InstrumentFactory')

class VideoMusikerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = m2m_video_musiker
    video = factory.SubFactory('DBentry.factories.models.VideoFactory')
    musiker = factory.SubFactory('DBentry.factories.models.MusikerFactory')

