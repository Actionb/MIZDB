"""
Provide text summaries for model objects.

The get_summaries function takes a queryset and returns OrderedDicts which
contain the values for each object in the queryset.
"""
from collections import OrderedDict
from typing import Any, Callable, Iterable, Iterator, Optional, Type, TypeVar

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Model, QuerySet

from dbentry import models as _models
from dbentry.utils.text import concat_limit

ModelClass = TypeVar("ModelClass", bound=Type[Model])  # a django model class
ModelObject = TypeVar("ModelObject", bound=Model)  # an instance of a model class

# A mapping of model class to model parser.
registry: dict = {}


def get_summaries(queryset: QuerySet) -> Iterator[OrderedDict]:
    """
    For each model object in 'queryset' return an OrderedDict of values that
    summarize the object.
    """
    if queryset.model not in registry:
        raise KeyError(f"No parser registered for model {queryset.model}.")
    return registry[queryset.model]().get_summaries(queryset)


def _register(model: ModelClass) -> Callable:
    """Register the given model class with the decorated model parser class."""

    def inner(cls: Type['Parser']) -> Type['Parser']:
        registry[model] = cls
        return cls

    return inner


def _concat(objects: Iterable, sep: str = "; "):
    return concat_limit(objects, sep=sep, width=0)


def _get_array_agg(path: str, ordering: Optional[str] = None) -> ArrayAgg:
    """Return a Postgres ArrayAgg aggregation on 'path'."""
    if not ordering:
        ordering = path
    return ArrayAgg(path, distinct=True, ordering=ordering)


def _bool(v: Any) -> str:
    return 'Ja' if bool(v) else 'Nein'


class Parser:
    """
    Provide summaries of model objects in the form of OrderedDicts for each
    object.
    """

    # arguments for QuerySet.select_related and prefetch_related
    select_related: Iterable = ()
    prefetch_related: Iterable = ()

    def get_annotations(self) -> dict:
        """Return annotation declarations to be added to the queryset."""
        return {}  # pragma: no cover

    def modify_queryset(self, queryset: QuerySet) -> QuerySet:
        """Modify the root queryset (f.ex. add annotations)."""
        if self.select_related:
            try:
                queryset = queryset.select_related(*self.select_related)
            except TypeError:
                # select_related() after .values() or .values_list()
                # Forgo queryset optimizations if the queryset is unsuitable.
                pass
        if self.prefetch_related:
            queryset = queryset.prefetch_related(*self.prefetch_related)
        return queryset.annotate(**self.get_annotations())

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        """Return an OrderedDict summary of the given model object 'obj'."""
        raise NotImplementedError("Subclasses must implement this method.")  # pragma: no cover

    def get_summaries(self, queryset: QuerySet) -> Iterator[OrderedDict]:
        """Yield summaries (OrderedDicts) for each object in 'queryset'."""
        for obj in self.modify_queryset(queryset):  # pragma: no cover
            yield self.get_summary(obj)


@_register(_models.Person)
class PersonParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'autor_list': _get_array_agg('autor___name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Person',
                'ID': obj.id,
                'Vorname': obj.vorname,
                'Nachname': obj.nachname,
                'Normdatei ID': obj.gnd_id,
                'Normdatei Name': obj.gnd_name,
                'Link DNB': obj.dnb_url,
                'Beschreibung': obj.beschreibung,
                'Webseiten': _concat(obj.url_list),
                'Musiker': _concat(obj.musiker_list),
                'Autoren': _concat(obj.autor_list),
                'Orte': _concat(obj.ort_list),
            }
        )


@_register(_models.Musiker)
class MusikerParser(Parser):
    select_related = ['person']
    prefetch_related = ['musikeralias_set', 'urls']

    def get_annotations(self) -> dict:
        return {
            'band_list': _get_array_agg('band__band_name'),
            'genre_list': _get_array_agg('genre__genre'),
            'instrument_list': _get_array_agg('instrument__instrument'),
            'alias_list': _get_array_agg('musikeralias__alias'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Musiker',
                'ID': obj.id,
                'Künstlername': obj.kuenstler_name,
                'Personen': obj.person,
                'Beschreibung': obj.beschreibung,
                'Webseiten': _concat(obj.url_list),
                'Genres': _concat(obj.genre_list),
                'Aliases': _concat(obj.alias_list),
                'Bands': _concat(obj.band_list),
                'Orte': _concat(obj.ort_list),
                'Instrumente': _concat(obj.instrument_list),
            }
        )


@_register(_models.Band)
class BandParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'alias_list': _get_array_agg('bandalias__alias'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Band',
                'ID': obj.id,
                'Bandname': obj.band_name,
                'Beschreibung': obj.beschreibung,
                'Aliases': _concat(obj.alias_list),
                'Webseiten': _concat(obj.url_list),
                'Genres': _concat(obj.genre_list),
                'Musiker': _concat(obj.musiker_list),
                'Orte': _concat(obj.ort_list),
            }
        )


@_register(_models.Autor)
class AutorParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'magazin_list': _get_array_agg('magazin__magazin_name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Autor',
                'ID': obj.id,
                'Name': obj.person,
                'Kürzel': obj.kuerzel,
                'Beschreibung': obj.beschreibung,
                'Webseiten': _concat(obj.url_list),
                'Magazine': _concat(obj.magazin_list),
            }
        )


@_register(_models.Ausgabe)
class AusgabeParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'jahr_list': _get_array_agg('ausgabejahr__jahr'),
            'num_list': _get_array_agg('ausgabenum__num'),
            'lnum_list': _get_array_agg('ausgabelnum__lnum'),
            'monat_list': _get_array_agg('ausgabemonat__monat__monat'),
            'audio_list': _get_array_agg('audio__titel'),
            'video_list': _get_array_agg('video__titel'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Ausgabe',
                'ID': obj.id,
                'Name': obj._name,
                'Magazin': obj.magazin,
                'Bearbeitungsstatus': obj.status,
                'Ist Sonderausgabe': _bool(obj.sonderausgabe),
                'Erscheinungsdatum': obj.e_datum,
                'Jahrgang': obj.jahrgang,
                'Beschreibung': obj.beschreibung,
                'Ausgabennummern': _concat(obj.num_list),
                'Monate': _concat(obj.monat_list),
                'Laufende Nummern': _concat(obj.lnum_list),
                'Jahre': _concat(obj.jahr_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Magazin)
class MagazinParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'verlag_list': _get_array_agg('verlag__verlag_name'),
            'herausgeber_list': _get_array_agg('herausgeber__herausgeber'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Magazin',
                'ID': obj.id,
                'Name': obj.magazin_name,
                'Ist Fanzine': _bool(obj.fanzine),
                'ISSN': obj.issn,
                'Beschreibung': obj.beschreibung,
                'Webseiten': _concat(obj.url_list),
                'Genres': _concat(obj.genre_list),
                'Verlage': _concat(obj.verlag_list),
                'Herausgeber': _concat(obj.herausgeber_list),
                'Orte': _concat(obj.ort_list),
            }
        )


@_register(_models.Artikel)
class ArtikelParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'autor_list': _get_array_agg('autor___name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'band_list': _get_array_agg('band__band_name'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'genre_list': _get_array_agg('genre__genre'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'person_list': _get_array_agg('person___name'),
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Artikel',
                'ID': obj.id,
                'Ausgabe': f"{obj.ausgabe} ({obj.ausgabe.magazin})",
                'Schlagzeile': obj.schlagzeile,
                'Seite': f"{obj.seite}{obj.seitenumfang}",
                'Zusammenfassung': obj.zusammenfassung,
                'Beschreibung': obj.beschreibung,
                'Autoren': _concat(obj.autor_list),
                'Musiker': _concat(obj.musiker_list),
                'Bands': _concat(obj.band_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Genres': _concat(obj.genre_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(
                    f"{v.name} ({v.spielort})" for v in obj.veranstaltung.order_by('name')
                ),
                'Personen': _concat(obj.person_list),
            }
        )


@_register(_models.Buch)
class BuchParser(Parser):
    select_related = ['schriftenreihe']

    def get_annotations(self) -> dict:
        return {
            'autor_list': _get_array_agg('autor___name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'band_list': _get_array_agg('band__band_name'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'genre_list': _get_array_agg('genre__genre'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'person_list': _get_array_agg('person___name'),
            'herausgeber_list': _get_array_agg('herausgeber__herausgeber'),
            'verlag_list': _get_array_agg('verlag__verlag_name'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Buch',
                'ID': obj.id,
                'Titel': obj.titel,
                'Seitenumfang': obj.seitenumfang,
                'Jahr': obj.jahr,
                'Auflage': obj.auflage,
                'Schriftenreihe': obj.schriftenreihe,
                'Sammelband': obj.buchband,
                'Ist Sammelband': _bool(obj.is_buchband),
                'ISBN': obj.ISBN,
                'EAN': obj.EAN,
                'Sprache': obj.sprache,
                'Titel (Original)': obj.titel_orig,
                'Jahr (Original)': obj.jahr_orig,
                'Beschreibung': obj.beschreibung,
                # TODO: include related Buch objects (if Sammelband)?
                # 'Bücher': None,
                'Autoren': _concat(obj.autor_list),
                'Musiker': _concat(obj.musiker_list),
                'Bands': _concat(obj.band_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Genres': _concat(obj.genre_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Personen': _concat(obj.person_list),
                'Herausgeber': _concat(obj.herausgeber_list),
                'Verlage': _concat(obj.verlag_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Audio)
class AudioParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'band_list': _get_array_agg('band__band_name'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'genre_list': _get_array_agg('genre__genre'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'person_list': _get_array_agg('person___name'),
            'plattenfirma_list': _get_array_agg('plattenfirma__name'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Audio Material',
                'ID': obj.id,
                'Titel': obj.titel,
                'Anz. Tracks': obj.tracks,
                'Laufzeit': obj.laufzeit,
                'Jahr': obj.jahr,
                'Land der Pressung': obj.land_pressung,
                'Ist Originalmaterial': _bool(obj.original),
                'Quelle': obj.quelle,
                'Speichermedium': obj.medium,
                'Anzahl': obj.medium_qty,
                'Plattennummer': obj.plattennummer,
                'Release ID (discogs)': obj.release_id,
                'Link discogs.com': obj.discogs_url,
                'Beschreibung': obj.beschreibung,
                'Musiker': _concat(obj.musiker_list),
                'Bands': _concat(obj.band_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Genres': _concat(obj.genre_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Personen': _concat(obj.person_list),
                'Plattenfirmen': _concat(obj.plattenfirma_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Plakat)
class PlakatParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'genre_list': _get_array_agg('genre__genre'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'band_list': _get_array_agg('band__band_name'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'person_list': _get_array_agg('person___name'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Plakat',
                'ID': obj.id,
                'Titel': obj.titel,
                'Signatur': obj.signatur,
                'Größe': obj.size,
                'Zeitangabe': obj.datum,
                'Beschreibung': obj.beschreibung,
                'Bildreihe': obj.reihe,
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Genres': _concat(obj.genre_list),
                'Musiker': _concat(obj.musiker_list),
                'Bands': _concat(obj.band_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Personen': _concat(obj.person_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Dokument)
class DokumentParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'person_list': _get_array_agg('person___name'),
            'band_list': _get_array_agg('band__band_name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Dokument',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Genres': _concat(obj.genre_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Personen': _concat(obj.person_list),
                'Bands': _concat(obj.band_list),
                'Musiker': _concat(obj.musiker_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Memorabilien)
class MemorabilienParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'person_list': _get_array_agg('person___name'),
            'band_list': _get_array_agg('band__band_name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Memorabilia',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Genres': _concat(obj.genre_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Personen': _concat(obj.person_list),
                'Bands': _concat(obj.band_list),
                'Musiker': _concat(obj.musiker_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Technik)
class TechnikParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'person_list': _get_array_agg('person___name'),
            'band_list': _get_array_agg('band__band_name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Technik',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Genres': _concat(obj.genre_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Personen': _concat(obj.person_list),
                'Bands': _concat(obj.band_list),
                'Musiker': _concat(obj.musiker_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Video)
class VideoParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'band_list': _get_array_agg('band__band_name'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'genre_list': _get_array_agg('genre__genre'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'person_list': _get_array_agg('person___name'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Video Material',
                'ID': obj.id,
                'Titel': obj.titel,
                'Laufzeit': obj.laufzeit,
                'Jahr': obj.jahr,
                'Quelle': obj.quelle,
                'Ist Originalmaterial': _bool(obj.original),
                'Release ID (discogs)': obj.release_id,
                'Link discogs.com': obj.discogs_url,
                'Speichermedium': obj.medium,
                'Anzahl': obj.medium_qty,
                'Beschreibung': obj.beschreibung,
                'Musiker': _concat(obj.musiker_list),
                'Bands': _concat(obj.band_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Genres': _concat(obj.genre_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Personen': _concat(obj.person_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Datei)
class DateiParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'person_list': _get_array_agg('person___name'),
            'band_list': _get_array_agg('band__band_name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Datei',
                'ID': obj.id,
                'Titel': obj.titel,
                'Media Typ': obj.media_typ,
                'Datei-Pfad': obj.datei_pfad,
                'Provenienz': obj.provenienz,
                'Beschreibung': obj.beschreibung,
                'Genres': _concat(obj.genre_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Musiker': _concat(obj.musiker_list),
                'Bands': _concat(obj.band_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Personen': _concat(obj.person_list),
            }
        )


@_register(_models.Brochure)
class BrochureParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'jahr_list': _get_array_agg('jahre__jahr'),
            'genre_list': _get_array_agg('genre__genre'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'url_list': _get_array_agg('urls__url'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Broschüre',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Beschreibung': obj.beschreibung,
                'Webseiten': _concat(obj.url_list),
                'Jahre': _concat(obj.jahr_list),
                'Genres': _concat(obj.genre_list),
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Kalender)
class KalenderParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'jahr_list': _get_array_agg('jahre__jahr'),
            'genre_list': _get_array_agg('genre__genre'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'url_list': _get_array_agg('urls__url'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Programmheft',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Beschreibung': obj.beschreibung,
                'Webseiten': _concat(obj.url_list),
                'Jahre': _concat(obj.jahr_list),
                'Genres': _concat(obj.genre_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Katalog)
class KatalogParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'jahr_list': _get_array_agg('jahre__jahr'),
            'genre_list': _get_array_agg('genre__genre'),
            'url_list': _get_array_agg('urls__url'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Warenkatalog',
                'ID': obj.id,
                'Titel': obj.titel,
                'Art d. Kataloges': obj.art,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Beschreibung': obj.beschreibung,
                'Webseiten': _concat(obj.url_list),
                'Jahre': _concat(obj.jahr_list),
                'Genres': _concat(obj.genre_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )


@_register(_models.Foto)
class FotoParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'genre_list': _get_array_agg('genre__genre'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'band_list': _get_array_agg('band__band_name'),
            'ort_list': _get_array_agg('ort___name'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'person_list': _get_array_agg('person___name'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj: ModelObject) -> OrderedDict:
        return OrderedDict(
            {
                'Objekt': 'Foto',
                'ID': obj.id,
                'Titel': obj.titel,
                'Größe': obj.size,
                'Art des Fotos': obj.typ,
                'Zeitangabe': obj.datum,
                'Ist Farbfoto': _bool(obj.farbe),
                'Bildreihe': obj.reihe,
                'Rechteinhaber': obj.owner,
                'Beschreibung': obj.beschreibung,
                'Schlagwörter': _concat(obj.schlagwort_list),
                'Genres': _concat(obj.genre_list),
                'Musiker': _concat(obj.musiker_list),
                'Bands': _concat(obj.band_list),
                'Orte': _concat(obj.ort_list),
                'Spielorte': _concat(obj.spielort_list),
                'Veranstaltungen': _concat(obj.veranstaltung_list),
                'Personen': _concat(obj.person_list),
                'Bestände': _concat(obj.bestand_list),
            }
        )
