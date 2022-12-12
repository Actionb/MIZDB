"""
Provide text summaries of model objects.

The get_summaries function, which takes a queryset as argument, returns a
generator of OrderedDicts which contain the values for each object in the
queryset.
"""
from collections import OrderedDict

from django.contrib.postgres.aggregates import ArrayAgg

from dbentry import models as _models

registry = {}


def register(model):
    def inner(cls):
        registry[model] = cls
        return cls

    return inner


def get_summaries(queryset):
    if queryset.model not in registry:
        raise KeyError(f"No parser registered for model {queryset.model}.")
    return registry[queryset.model]().get_summaries(queryset)


def summary_action(_model_admin, _request, queryset):
    """
    Function for a model admin action that summarizes the selected items in
    text form.
    """
    result = ""
    for d in get_summaries(queryset):
        if result:
            result += "<hr>"
        for k, v in d.items():
            # TODO: for 'many' relations, have v be a list of values and then
            #  use <ul>?
            result += f"<p>{k}: {v}</p>"
    from django.http import HttpResponse
    from django.utils.safestring import mark_safe
    return HttpResponse(mark_safe(result))
summary_action.short_description = 'Zusammenfassende textliche Darstellung'  # noqa


def concat(objects, sep="; "):
    # TODO: use utils.concat_limit (rename concat_limit to just 'concat'?)
    return sep.join(str(o) for o in objects if o)


def _get_array_agg(path, ordering=None):
    """Return a Postgres ArrayAgg aggregation on 'path'."""
    if not ordering:
        ordering = path
    return ArrayAgg(path, distinct=True, ordering=ordering)


def _bool(v):
    return 'Ja' if bool(v) else 'Nein'


class Parser:
    select_related = None
    prefetch_related = None

    def get_annotations(self) -> dict:
        return {}

    def modify_queryset(self, queryset):
        """Modify the root queryset (f.ex. add annotations)."""
        if self.select_related:
            queryset = queryset.select_related(*self.select_related)
        if self.prefetch_related:
            queryset = queryset.prefetch_related(*self.prefetch_related)
        return queryset.annotate(**self.get_annotations())

    def get_summary(self, obj):
        raise NotImplementedError("Subclasses must implement this method.")

    def get_summaries(self, queryset):
        for obj in self.modify_queryset(queryset):
            yield self.get_summary(obj)


@register(_models.Person)
class PersonParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'autor_list': _get_array_agg('autor___name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj) -> dict:
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
                'Webseiten': concat(obj.url_list),
                'Musiker': concat(obj.musiker_list),
                'Autoren': concat(obj.autor_list),
                'Orte': concat(obj.ort_list),
            }
        )


@register(_models.Musiker)
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

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Musiker',
                'ID': obj.id,
                'Künstlername': obj.kuenstler_name,
                'Personen': obj.person,
                'Beschreibung': obj.beschreibung,
                'Webseiten': concat(obj.url_list),
                'Genres': concat(obj.genre_list),
                'Aliases': concat(obj.alias_list),
                'Bands': concat(obj.band_list),
                'Orte': concat(obj.ort_list),
                'Instrumente': concat(obj.instrument_list),
            }
        )


@register(_models.Band)
class BandParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'alias_list': _get_array_agg('bandalias__alias'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Band',
                'ID': obj.id,
                'Bandname': obj.band_name,
                'Beschreibung': obj.beschreibung,
                'Aliases': concat(obj.alias_list),
                'Webseiten': concat(obj.url_list),
                'Genres': concat(obj.genre_list),
                'Musiker': concat(obj.musiker_list),
                'Orte': concat(obj.ort_list),
            }
        )


@register(_models.Autor)
class AutorParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'magazin_list': _get_array_agg('magazin__magazin_name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Autor',
                'ID': obj.id,
                'Name': obj.person,
                'Kürzel': obj.kuerzel,
                'Beschreibung': obj.beschreibung,
                'Webseiten': concat(obj.url_list),
                'Magazine': concat(obj.magazin_list),
            }
        )


@register(_models.Ausgabe)
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

    def get_summary(self, obj) -> dict:
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
                'Ausgabennummern': concat(obj.num_list),
                'Monate': concat(obj.monat_list),
                'Laufende Nummern': concat(obj.lnum_list),
                'Jahre': concat(obj.jahr_list),
                'Bestände': concat(obj.bestand_list),
                # 'Artikel': None,
                # 'base brochures': None,
                # 'Audio Materialien': None,
                # 'Video Materialien': None,
            }
        )


@register(_models.Magazin)
class MagazinParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'verlag_list': _get_array_agg('verlag__verlag_name'),
            'herausgeber_list': _get_array_agg('herausgeber__herausgeber'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'),
        }

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Magazin',
                'ID': obj.id,
                'Name': obj.magazin_name,
                'Ist Fanzine': _bool(obj.fanzine),
                'ISSN': obj.issn,
                'Beschreibung': obj.beschreibung,
                # 'Ausgaben': None,
                'Webseiten': concat(obj.url_list),
                'Genres': concat(obj.genre_list),
                'Verlage': concat(obj.verlag_list),
                'Herausgeber': concat(obj.herausgeber_list),
                'Orte': concat(obj.ort_list),
            }
        )


@register(_models.Artikel)
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

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Artikel',
                'ID': obj.id,
                'Ausgabe': f"{obj.ausgabe} ({obj.ausgabe.magazin})",
                'Schlagzeile': obj.schlagzeile,
                'Seite': f"{obj.seite}{obj.seitenumfang}",
                'Zusammenfassung': obj.zusammenfassung,
                'Beschreibung': obj.beschreibung,
                'Autoren': concat(obj.autor_list),
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(
                    f"{v.name} ({v.spielort})" for v in obj.veranstaltung.order_by('name')
                ),
                'Personen': concat(obj.person_list),
            }
        )


@register(_models.Buch)
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

    def get_summary(self, obj) -> dict:
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
                'Autoren': concat(obj.autor_list),
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
                'Herausgeber': concat(obj.herausgeber_list),
                'Verlage': concat(obj.verlag_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Audio)
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

    def get_summary(self, obj) -> dict:
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
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
                'Plattenfirmen': concat(obj.plattenfirma_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Plakat)
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

    def get_summary(self, obj) -> dict:
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
                # 'Datei-Quellen': None,
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Dokument)
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

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Dokument',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                # 'Datei-Quellen': None,
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Personen': concat(obj.person_list),
                'Bands': concat(obj.band_list),
                'Musiker': concat(obj.musiker_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Memorabilien)
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

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Memorabilia',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                # 'Datei-Quellen': None,
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Personen': concat(obj.person_list),
                'Bands': concat(obj.band_list),
                'Musiker': concat(obj.musiker_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Technik)
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

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Technik',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Personen': concat(obj.person_list),
                'Bands': concat(obj.band_list),
                'Musiker': concat(obj.musiker_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Video)
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

    def get_summary(self, obj) -> dict:
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
                # 'Video-Musiker': None,
                # 'Datei-Quellen': None,
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Datei)
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

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Datei',
                'ID': obj.id,
                'Titel': obj.titel,
                'Media Typ': obj.media_typ,
                'Datei-Pfad': obj.datei_pfad,
                'Provenienz': obj.provenienz,
                'Beschreibung': obj.beschreibung,
                # 'Datei-Quellen': None,
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
            }
        )


@register(_models.Brochure)
class BrochureParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'jahr_list': _get_array_agg('jahre__jahr'),
            'genre_list': _get_array_agg('genre__genre'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'url_list': _get_array_agg('urls__url'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Broschüre',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Beschreibung': obj.beschreibung,
                'Webseiten': concat(obj.url_list),
                'Jahre': concat(obj.jahr_list),
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Kalender)
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

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Programmheft',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Beschreibung': obj.beschreibung,
                'Webseiten': concat(obj.url_list),
                'Jahre': concat(obj.jahr_list),
                'Genres': concat(obj.genre_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Katalog)
class KatalogParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'jahr_list': _get_array_agg('jahre__jahr'),
            'genre_list': _get_array_agg('genre__genre'),
            'url_list': _get_array_agg('urls__url'),
            'bestand_list': _get_array_agg('bestand__lagerort___name')
        }

    def get_summary(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Warenkatalog',
                'ID': obj.id,
                'Titel': obj.titel,
                'Art d. Kataloges': obj.art,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Beschreibung': obj.beschreibung,
                'Webseiten': concat(obj.url_list),
                'Jahre': concat(obj.jahr_list),
                'Genres': concat(obj.genre_list),
                'Bestände': concat(obj.bestand_list),
            }
        )


@register(_models.Foto)
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

    def get_summary(self, obj) -> dict:
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
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
                'Bestände': concat(obj.bestand_list),
            }
        )
