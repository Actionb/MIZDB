"""
Provide useful text representations of model objects.

The get_text_representations function, which takes a queryset as argument,
returns a generator of OrderedDicts which contain the values for each object in
the queryset.
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


def get_text_representations(queryset):
    if queryset.model not in registry:
        raise KeyError(f"No parser registered for model {queryset.model}.")
    return registry[queryset.model]().get_text_representations(queryset)


def text_repr_action(_model_admin, _request, queryset):
    """
    Function for a model admin action that displays the selected items in text
    form.
    """
    result = ""
    for d in get_text_representations(queryset):
        if result:
            result += "<hr>"
        for k, v in d.items():
            # TODO: for 'many' relations, have v be a list of values and then
            #  use <ul>?
            result += f"<p>{k}: {v}</p>"
    from django.http import HttpResponse
    from django.utils.safestring import mark_safe
    return HttpResponse(mark_safe(result))


text_repr_action.short_description = 'textliche Darstellung'  # noqa


def concat(objects, sep="; "):
    # TODO: use utils.concat_limit (rename concat_limit to just 'concat'?)
    return sep.join(str(o) for o in objects if o)


def _get_array_agg(path, ordering=None):
    """Return a Postgres ArrayAgg aggregation on 'path'."""
    if not ordering:
        ordering = path
    return ArrayAgg(path, distinct=True, ordering=ordering)


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

    def get_text_repr(self, obj):
        raise NotImplementedError("Subclasses must implement this method.")

    def get_text_representations(self, queryset):
        for obj in self.modify_queryset(queryset):
            yield self.get_text_repr(obj)


@register(_models.Person)
class PersonParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'autor_list': _get_array_agg('autor___name'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'), 
        }

    def get_text_repr(self, obj) -> dict:
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

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Musiker',
                'ID': obj.id,
                'Künstlername': obj.kuenstler_name,
                'Beschreibung': obj.beschreibung,
                'Person': obj.person,
                'Bands': concat(obj.band_list),
                'Aliases': concat(obj.musikeralias_set.all()),
                'Webseiten': concat(obj.url_list),
                'Genres': concat(obj.genre_list),
                'Instrumente': concat(obj.instrument_list),
                'Orte': concat(obj.ort_list),
            }
        )


@register(_models.Band)
class BandParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'ort_list': _get_array_agg('orte___name'),
            'url_list': _get_array_agg('urls__url'), 
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Band',
                'ID': obj.id,
                'Bandname': obj.band_name,
                'Beschreibung': obj.beschreibung,
                'Aliases': concat(obj.bandalias_set.all()),
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

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Autor',
                'ID': obj.id,
                'Kürzel': obj.kuerzel,
                'Beschreibung': obj.beschreibung,
                'Person': obj.person,
                'Webseiten': concat(obj.url_list),
                'Magazine': None,
            }
        )


@register(_models.Ausgabe)
class AusgabeParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'audio_list': _get_array_agg('audio__titel'),
            'video_list': _get_array_agg('video__titel'),
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Ausgabe',
                'ID': obj.id,
                'Bearbeitungsstatus': obj.status,
                'Erscheinungsdatum': obj.e_datum,
                'Jahrgang': obj.jahrgang,
                'Sonderausgabe': obj.sonderausgabe,
                'Beschreibung': obj.beschreibung,
                'Magazin': obj.magazin,
                'Jahre': None,
                'Ausgabennummer': None,
                'Laufende Nummer': None,
                'Ausgabe-Monate': None,
                'Artikel': None,
                'Bestände': None,
                'base brochures': None,
                'Audio Materialien': None,
                'Video Materialien': None,
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

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Magazin',
                'ID': obj.id,
                'Magazin': obj.magazin_name,
                'Ausgaben Merkmal': obj.ausgaben_merkmal,
                'Fanzine': obj.fanzine,
                'ISSN': obj.issn,
                'Beschreibung': obj.beschreibung,
                'Ausgaben': None,
                'Webseiten': concat(obj.url_list),
                'Genres': concat(obj.genre_list),
                'Verlage': None,
                'Herausgeber': None,
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

    def get_text_repr(self, obj) -> dict:
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
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Buch',
                'ID': obj.id,
                'Titel': obj.titel,
                'Titel (Original)': obj.titel_orig,
                'Seitenumfang': obj.seitenumfang,
                'Jahr': obj.jahr,
                'Jahr (Original)': obj.jahr_orig,
                'Auflage': obj.auflage,
                'EAN': obj.EAN,
                'ISBN': obj.ISBN,
                'Ist Sammelband': obj.is_buchband,
                'Beschreibung': obj.beschreibung,
                'Schriftenreihe': obj.schriftenreihe,
                'Sammelband': obj.buchband,
                'Sprache': obj.sprache,
                'Datei-Quellen': None,
                'Bücher': None,
                'Bestände': None,
                'Autoren': None,
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
                'Herausgeber': None,
                'Verlage': None,
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
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Audio Material',
                'ID': obj.id,
                'Titel': obj.titel,
                'Anz. Tracks': obj.tracks,
                'Laufzeit': obj.laufzeit,
                'Jahr': obj.jahr,
                'Land der Pressung': obj.land_pressung,
                'Quelle': obj.quelle,
                'Originalmaterial': obj.original,
                'Plattennummer': obj.plattennummer,
                'Release ID (discogs)': obj.release_id,
                'Link discogs.com': obj.discogs_url,
                'Beschreibung': obj.beschreibung,
                'Speichermedium': obj.medium,
                'Anzahl': obj.medium_qty,
                'Audio-Musiker': None,
                'Datei-Quellen': None,
                'Bestände': None,
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
                'Plattenfirmen': None,
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
        }

    def get_text_repr(self, obj) -> dict:
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
                'Datei-Quellen': None,
                'Bestände': None,
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
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
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Dokument',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Datei-Quellen': None,
                'Bestände': None,
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Personen': concat(obj.person_list),
                'Bands': concat(obj.band_list),
                'Musiker': concat(obj.musiker_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
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
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Memorabilia',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Datei-Quellen': None,
                'Bestände': None,
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Personen': concat(obj.person_list),
                'Bands': concat(obj.band_list),
                'Musiker': concat(obj.musiker_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
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
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Technik',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Bestände': None,
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Personen': concat(obj.person_list),
                'Bands': concat(obj.band_list),
                'Musiker': concat(obj.musiker_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
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
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Video Material',
                'ID': obj.id,
                'Titel': obj.titel,
                'Laufzeit': obj.laufzeit,
                'Jahr': obj.jahr,
                'Quelle': obj.quelle,
                'Originalmaterial': obj.original,
                'Release ID (discogs)': obj.release_id,
                'Link discogs.com': obj.discogs_url,
                'Beschreibung': obj.beschreibung,
                'Speichermedium': obj.medium,
                'Anzahl': obj.medium_qty,
                'Video-Musiker': None,
                'Datei-Quellen': None,
                'Bestände': None,
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
            }
        )


@register(_models.Bestand)
class BestandParser(Parser):

    def get_annotations(self) -> dict:
        return {
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Bestand',
                'Signatur': obj.signatur,
                'Lagerort': obj.lagerort,
                'Anmerkungen': obj.anmerkungen,
                'Provenienz': obj.provenienz,
                'Audio': obj.audio,
                'Ausgabe': obj.ausgabe,
                'Brochure': obj.brochure,
                'Buch': obj.buch,
                'Dokument': obj.dokument,
                'Foto': obj.foto,
                'Memorabilien': obj.memorabilien,
                'Plakat': obj.plakat,
                'Technik': obj.technik,
                'Video': obj.video,
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

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Datei',
                'ID': obj.id,
                'Titel': obj.titel,
                'Media Typ': obj.media_typ,
                'Datei': obj.datei_media,
                'Datei-Pfad': obj.datei_pfad,
                'Beschreibung': obj.beschreibung,
                'Provenienz': obj.provenienz,
                'Musiker': concat(obj.musiker_list),
                'Datei-Quellen': None,
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
                'Personen': concat(obj.person_list),
                'Bands': concat(obj.band_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
            }
        )


@register(_models.Brochure)
class BrochureParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'url_list': _get_array_agg('urls__url'), 
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Broschüre',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Beschreibung': obj.beschreibung,
                'Bestände': None,
                'Jahre': None,
                'Webseiten': concat(obj.url_list),
                'Genres': concat(obj.genre_list),
                'Schlagwörter': concat(obj.schlagwort_list),
            }
        )


@register(_models.Kalender)
class KalenderParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
            'url_list': _get_array_agg('urls__url'), 
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Programmheft',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Basebrochure ptr': obj.basebrochure_ptr,
                'Beschreibung': obj.beschreibung,
                'Bestände': None,
                'Jahre': None,
                'Webseiten': concat(obj.url_list),
                'Genres': concat(obj.genre_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
            }
        )


@register(_models.Katalog)
class KatalogParser(Parser):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'url_list': _get_array_agg('urls__url'), 
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Warenkatalog',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Ausgabe': obj.ausgabe,
                'Basebrochure ptr': obj.basebrochure_ptr,
                'Beschreibung': obj.beschreibung,
                'Art d. Kataloges': obj.art,
                'Bestände': None,
                'Jahre': None,
                'Webseiten': concat(obj.url_list),
                'Genres': concat(obj.genre_list),
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
        }

    def get_text_repr(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Foto',
                'ID': obj.id,
                'Titel': obj.titel,
                'Größe': obj.size,
                'Zeitangabe': obj.datum,
                'Art des Fotos': obj.typ,
                'Farbfoto': obj.farbe,
                'Rechteinhaber': obj.owner,
                'Beschreibung': obj.beschreibung,
                'Bildreihe': obj.reihe,
                'Bestände': None,
                'Schlagwörter': concat(obj.schlagwort_list),
                'Genres': concat(obj.genre_list),
                'Musiker': concat(obj.musiker_list),
                'Bands': concat(obj.band_list),
                'Orte': concat(obj.ort_list),
                'Spielorte': concat(obj.spielort_list),
                'Veranstaltungen': concat(obj.veranstaltung_list),
                'Personen': concat(obj.person_list),
            }
        )
