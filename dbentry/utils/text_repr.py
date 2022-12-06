"""
Provide useful text representations of model objects.

The get_documents function, which takes a queryset as argument, returns a
generator of OrderedDicts which contain the values for each object in the
queryset.
"""
from collections import OrderedDict

from django.contrib.postgres.aggregates import ArrayAgg

from dbentry import models as _models


# TODO: better name for "Document" -- text representer maybe?

registry = {}


def register(model):
    def inner(cls):
        registry[model] = cls
        return cls
    return inner


def get_documents(queryset):
    if queryset.model not in registry:
        raise KeyError(f"No documenter registered for model {queryset.model}.")
    return registry[queryset.model]().get_documents(queryset)


def text_repr_action(_model_admin, _request, queryset):
    """
    Function for a model admin action that displays the selected items in text
    form.
    """
    result = ""
    for d in get_documents(queryset):
        if result:
            result += "<hr>"
        for k, v in d.items():
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


class Document:
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

    def get_document(self, obj):
        raise NotImplementedError("Subclasses must implement this method.")

    def get_documents(self, queryset):
        for obj in self.modify_queryset(queryset):
            yield self.get_document(obj)


@register(_models.Person)
class PersonDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'orte_list': _get_array_agg('orte___name'),
        }

    def get_document(self, obj) -> dict:
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
                'Bemerkungen': obj.bemerkungen,
                'Webseiten': None,
                'Musiker': None,
                'Autoren': None,
                'Orte': None,
            }
        )


@register(_models.Musiker)
class MusikerDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'instrument_list': _get_array_agg('instrument__instrument'),
            'orte_list': _get_array_agg('orte___name'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Musiker',
                'ID': obj.id,
                'Künstlername': obj.kuenstler_name,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Person': obj.person,
                'Audio-Musiker': None,
                'Video-Musiker': None,
                'Musiker': None,
                'Aliases': None,
                'Webseiten': None,
                'Genres': None,
                'Instrumente': None,
                'Orte': None,
            }
        )


@register(_models.Genre)
class GenreDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Genre',
                'ID': obj.id,
                'Genre': obj.genre,
                'Aliases': None,
            }
        )


@register(_models.Band)
class BandDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'orte_list': _get_array_agg('orte___name'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Band',
                'ID': obj.id,
                'Bandname': obj.band_name,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Aliases': None,
                'Webseiten': None,
                'Genres': None,
                'Musiker': None,
                'Orte': None,
            }
        )


@register(_models.Autor)
class AutorDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'magazin_list': _get_array_agg('magazin__magazin_name'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Autor',
                'ID': obj.id,
                'Kürzel': obj.kuerzel,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Person': obj.person,
                'Webseiten': None,
                'Magazine': None,
            }
        )


@register(_models.Ausgabe)
class AusgabeDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'audio_list': _get_array_agg('audio__titel'),
            'video_list': _get_array_agg('video__titel'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Ausgabe',
                'ID': obj.id,
                'Bearbeitungsstatus': obj.status,
                'Erscheinungsdatum': obj.e_datum,
                'Jahrgang': obj.jahrgang,
                'Sonderausgabe': obj.sonderausgabe,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
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
class MagazinDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'verlag_list': _get_array_agg('verlag__verlag_name'),
            'herausgeber_list': _get_array_agg('herausgeber__herausgeber'),
            'orte_list': _get_array_agg('orte___name'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Magazin',
                'ID': obj.id,
                'Magazin': obj.magazin_name,
                'Ausgaben Merkmal': obj.ausgaben_merkmal,
                'Fanzine': obj.fanzine,
                'ISSN': obj.issn,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Ausgaben': None,
                'Webseiten': None,
                'Genres': None,
                'Verlage': None,
                'Herausgeber': None,
                'Orte': None,
            }
        )


@register(_models.Verlag)
class VerlagDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Verlag',
                'ID': obj.id,
                'Verlag': obj.verlag_name,
                'Sitz': obj.sitz,
            }
        )


@register(_models.Ort)
class OrtDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Ort',
                'ID': obj.id,
                'Stadt': obj.stadt,
                'Bundesland': obj.bland,
                'Land': obj.land,
                'Verlage': None,
                'Spielorte': None,
            }
        )


@register(_models.Bundesland)
class BundeslandDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Bundesland',
                'ID': obj.id,
                'Bundesland': obj.bland_name,
                'Code': obj.code,
                'Land': obj.land,
                'Orte': None,
            }
        )


@register(_models.Land)
class LandDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Land',
                'ID': obj.id,
                'Land': obj.land_name,
                'Code': obj.code,
                'Orte': None,
                'Bundesländer': None,
                'Audio Materialien': None,
            }
        )


@register(_models.Schlagwort)
class SchlagwortDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Schlagwort',
                'ID': obj.id,
                'Schlagwort': obj.schlagwort,
                'Aliases': None,
            }
        )


@register(_models.Artikel)
class ArtikelDocument(Document):

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
        }

    def get_document(self, obj) -> dict:
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
class BuchDocument(Document):

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

    def get_document(self, obj) -> dict:
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
                'Bemerkungen': obj.bemerkungen,
                'Schriftenreihe': obj.schriftenreihe,
                'Sammelband': obj.buchband,
                'Sprache': obj.sprache,
                'Datei-Quellen': None,
                'Bücher': None,
                'Bestände': None,
                'Autoren': None,
                'Musiker': None,
                'Bands': None,
                'Schlagwörter': None,
                'Genres': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
                'Personen': None,
                'Herausgeber': None,
                'Verlage': None,
            }
        )


@register(_models.Herausgeber)
class HerausgeberDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Herausgeber',
                'ID': obj.id,
                'Herausgeber': obj.herausgeber,
            }
        )


@register(_models.Instrument)
class InstrumentDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Instrument',
                'ID': obj.id,
                'Instrument': obj.instrument,
                'Kürzel': obj.kuerzel,
            }
        )


@register(_models.Audio)
class AudioDocument(Document):

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

    def get_document(self, obj) -> dict:
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
                'Bemerkungen': obj.bemerkungen,
                'Speichermedium': obj.medium,
                'Anzahl': obj.medium_qty,
                'Audio-Musiker': None,
                'Datei-Quellen': None,
                'Bestände': None,
                'Musiker': None,
                'Bands': None,
                'Schlagwörter': None,
                'Genres': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
                'Personen': None,
                'Plattenfirmen': None,
            }
        )


@register(_models.Plakat)
class PlakatDocument(Document):

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

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Plakat',
                'ID': obj.id,
                'Titel': obj.titel,
                'Signatur': obj.signatur,
                'Größe': obj.size,
                'Zeitangabe': obj.datum,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Bildreihe': obj.reihe,
                'Datei-Quellen': None,
                'Bestände': None,
                'Schlagwörter': None,
                'Genres': None,
                'Musiker': None,
                'Bands': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
                'Personen': None,
            }
        )


@register(_models.Dokument)
class DokumentDocument(Document):

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

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Dokument',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Datei-Quellen': None,
                'Bestände': None,
                'Genres': None,
                'Schlagwörter': None,
                'Personen': None,
                'Bands': None,
                'Musiker': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
            }
        )


@register(_models.Memorabilien)
class MemorabilienDocument(Document):

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

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Memorabilia',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Datei-Quellen': None,
                'Bestände': None,
                'Genres': None,
                'Schlagwörter': None,
                'Personen': None,
                'Bands': None,
                'Musiker': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
            }
        )


@register(_models.Spielort)
class SpielortDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Spielort',
                'ID': obj.id,
                'Name': obj.name,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Ort': obj.ort,
                'Webseiten': None,
                'Aliases': None,
                'Veranstaltungen': None,
            }
        )


@register(_models.Technik)
class TechnikDocument(Document):

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

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Technik',
                'ID': obj.id,
                'Titel': obj.titel,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Bestände': None,
                'Genres': None,
                'Schlagwörter': None,
                'Personen': None,
                'Bands': None,
                'Musiker': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
            }
        )


@register(_models.Veranstaltung)
class VeranstaltungDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'musiker_list': _get_array_agg('musiker__kuenstler_name'),
            'band_list': _get_array_agg('band__band_name'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
            'genre_list': _get_array_agg('genre__genre'),
            'person_list': _get_array_agg('person___name'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Veranstaltung',
                'ID': obj.id,
                'Name': obj.name,
                'Datum': obj.datum,
                'Spielort': obj.spielort,
                'Reihe': obj.reihe,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Aliases': None,
                'Webseiten': None,
                'Musiker': None,
                'Bands': None,
                'Schlagwörter': None,
                'Genres': None,
                'Personen': None,
            }
        )


@register(_models.Video)
class VideoDocument(Document):

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

    def get_document(self, obj) -> dict:
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
                'Bemerkungen': obj.bemerkungen,
                'Speichermedium': obj.medium,
                'Anzahl': obj.medium_qty,
                'Video-Musiker': None,
                'Datei-Quellen': None,
                'Bestände': None,
                'Musiker': None,
                'Bands': None,
                'Schlagwörter': None,
                'Genres': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
                'Personen': None,
            }
        )


@register(_models.Provenienz)
class ProvenienzDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Provenienz',
                'ID': obj.id,
                'Art der Provenienz': obj.typ,
                'Geber': obj.geber,
                'Bestände': None,
                'Dateien': None,
            }
        )


@register(_models.Geber)
class GeberDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Geber',
                'ID': obj.id,
                'Name': obj.name,
                'Provenienzen': None,
            }
        )


@register(_models.Lagerort)
class LagerortDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Lagerort',
                'ID': obj.id,
                'Ort': obj.ort,
                'Raum': obj.raum,
                'Regal': obj.regal,
                'Fach': obj.fach,
                'Ordner': obj.ordner,
                'Bestände': None,
            }
        )


@register(_models.Bestand)
class BestandDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
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
class DateiDocument(Document):

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

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Datei',
                'ID': obj.id,
                'Titel': obj.titel,
                'Media Typ': obj.media_typ,
                'Datei': obj.datei_media,
                'Datei-Pfad': obj.datei_pfad,
                'Beschreibung': obj.beschreibung,
                'Bemerkungen': obj.bemerkungen,
                'Provenienz': obj.provenienz,
                'Musiker': None,
                'Datei-Quellen': None,
                'Genres': None,
                'Schlagwörter': None,
                'Personen': None,
                'Bands': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
            }
        )


@register(_models.Plattenfirma)
class PlattenfirmaDocument(Document):

    def get_annotations(self) -> dict:
        return {
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Plattenfirma',
                'ID': obj.id,
                'Name': obj.name,
            }
        )


@register(_models.BaseBrochure)
class BaseBrochureDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'base brochure',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Bemerkungen': obj.bemerkungen,
                'Ausgabe': obj.ausgabe,
                'Bestände': None,
                'Jahre': None,
                'Webseiten': None,
                'Genres': None,
            }
        )


@register(_models.Brochure)
class BrochureDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'schlagwort_list': _get_array_agg('schlagwort__schlagwort'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Broschüre',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Bemerkungen': obj.bemerkungen,
                'Ausgabe': obj.ausgabe,
                'Basebrochure ptr': obj.basebrochure_ptr,
                'Beschreibung': obj.beschreibung,
                'Bestände': None,
                'Jahre': None,
                'Webseiten': None,
                'Genres': None,
                'Schlagwörter': None,
            }
        )


@register(_models.Kalender)
class KalenderDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
            'spielort_list': _get_array_agg('spielort__name'),
            'veranstaltung_list': _get_array_agg('veranstaltung__name'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Programmheft',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Bemerkungen': obj.bemerkungen,
                'Ausgabe': obj.ausgabe,
                'Basebrochure ptr': obj.basebrochure_ptr,
                'Beschreibung': obj.beschreibung,
                'Bestände': None,
                'Jahre': None,
                'Webseiten': None,
                'Genres': None,
                'Spielorte': None,
                'Veranstaltungen': None,
            }
        )


@register(_models.Katalog)
class KatalogDocument(Document):

    def get_annotations(self) -> dict:
        return {
            'genre_list': _get_array_agg('genre__genre'),
        }

    def get_document(self, obj) -> dict:
        return OrderedDict(
            {
                'Objekt': 'Warenkatalog',
                'ID': obj.id,
                'Titel': obj.titel,
                'Zusammenfassung': obj.zusammenfassung,
                'Bemerkungen': obj.bemerkungen,
                'Ausgabe': obj.ausgabe,
                'Basebrochure ptr': obj.basebrochure_ptr,
                'Beschreibung': obj.beschreibung,
                'Art d. Kataloges': obj.art,
                'Bestände': None,
                'Jahre': None,
                'Webseiten': None,
                'Genres': None,
            }
        )


@register(_models.Foto)
class FotoDocument(Document):

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

    def get_document(self, obj) -> dict:
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
                'Bemerkungen': obj.bemerkungen,
                'Bildreihe': obj.reihe,
                'Bestände': None,
                'Schlagwörter': None,
                'Genres': None,
                'Musiker': None,
                'Bands': None,
                'Orte': None,
                'Spielorte': None,
                'Veranstaltungen': None,
                'Personen': None,
            }
        )
