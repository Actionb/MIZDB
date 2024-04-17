"""Resources generated with this:

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MIZDB.settings.development")
django.setup()

from dbentry.site.views.edit import *  # noqa
from dbentry.export.base import *  # noqa

if __name__ == '__main__':
    with open("/tmp/mizdb_exports/generated.py", "w") as f:
        for model in miz_site.views:
            resource_class = resource_factory(model)
            f.write(resource_class().as_string())
            f.write("\n\n")
"""

from dbentry import models as _models
from dbentry.export.base import AnnotationField, MIZResource, CachedQuerysetField
from dbentry.utils.query import string_list


class AudioResource(MIZResource):
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Audio.objects.annotate(musiker_list=string_list("musiker__kuenstler_name")),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Audio.objects.annotate(band_list=string_list("band__band_name")),
    )
    schlagwort_list = AnnotationField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        expr=string_list("schlagwort__schlagwort"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    ort_list = AnnotationField(
        attribute="ort_list",
        column_name="Orte",
        expr=string_list("ort___name", sep="; "),
    )
    spielort_list = AnnotationField(
        attribute="spielort_list",
        column_name="Spielorte",
        expr=string_list("spielort__name"),
    )
    veranstaltung_list = AnnotationField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        expr=string_list("veranstaltung__name"),
    )
    person_list = AnnotationField(
        attribute="person_list",
        column_name="Personen",
        expr=string_list("person___name"),
    )
    plattenfirma_list = AnnotationField(
        attribute="plattenfirma_list",
        column_name="Plattenfirmen",
        expr=string_list("plattenfirma__name"),
    )
    ausgabe_list = AnnotationField(
        attribute="ausgabe_list",
        column_name="Ausgaben",
        expr=string_list("ausgabe___name"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Audio
        fields = [
            "id",
            "titel",
            "laufzeit",
            "tracks",
            "jahr",
            "land_pressung",
            "plattennummer",
            "quelle",
            "original",
            "medium",
            "medium_qty",
            "discogs_url",
            "release_id",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "plattenfirma_list",
            "ausgabe_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "titel",
            "laufzeit",
            "tracks",
            "jahr",
            "land_pressung",
            "plattennummer",
            "quelle",
            "original",
            "medium",
            "medium_qty",
            "discogs_url",
            "release_id",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "plattenfirma_list",
            "ausgabe_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"land_pressung": {"field": "land_name"}, "medium": {"field": "medium"}}
        select_related = ["land_pressung", "medium"]


class AusgabeResource(MIZResource):
    ausgabenum_list = AnnotationField(
        attribute="ausgabenum_list",
        column_name="Ausgabennummern",
        expr=string_list("ausgabenum__num"),
    )
    ausgabemonat_list = AnnotationField(
        attribute="ausgabemonat_list",
        column_name="Monate",
        expr=string_list("ausgabemonat__monat__abk"),
    )
    ausgabelnum_list = AnnotationField(
        attribute="ausgabelnum_list",
        column_name="Laufende Nummer",
        expr=string_list("ausgabelnum__lnum"),
    )
    ausgabejahr_list = AnnotationField(
        attribute="ausgabejahr_list",
        column_name="erschienen im Jahr",
        expr=string_list("ausgabejahr__jahr"),
    )
    audio_list = AnnotationField(
        attribute="audio_list",
        column_name="Audio Materialien",
        expr=string_list("audio__titel"),
    )
    video_list = AnnotationField(
        attribute="video_list",
        column_name="Video Materialien",
        expr=string_list("video__titel"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Ausgabe
        fields = [
            "id",
            "magazin",
            "status",
            "sonderausgabe",
            "e_datum",
            "jahrgang",
            "ausgabenum_list",
            "ausgabemonat_list",
            "ausgabelnum_list",
            "ausgabejahr_list",
            "audio_list",
            "video_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "magazin",
            "status",
            "sonderausgabe",
            "e_datum",
            "jahrgang",
            "ausgabenum_list",
            "ausgabemonat_list",
            "ausgabelnum_list",
            "ausgabejahr_list",
            "audio_list",
            "video_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"magazin": {"field": "magazin_name"}}
        select_related = ["magazin"]


class AutorResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    magazin_list = AnnotationField(
        attribute="magazin_list",
        column_name="Magazine",
        expr=string_list("magazin__magazin_name"),
    )

    class Meta:
        model = _models.Autor
        fields = ["id", "person", "kuerzel", "urls_list", "magazin_list", "beschreibung"]
        export_order = ["id", "person", "kuerzel", "urls_list", "magazin_list", "beschreibung"]
        widgets = {"person": {"field": "_name"}}
        select_related = ["person"]


class ArtikelResource(MIZResource):
    autor_list = AnnotationField(
        attribute="autor_list",
        column_name="Autoren",
        expr=string_list("autor___name"),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Artikel.objects.annotate(musiker_list=string_list("musiker__kuenstler_name")),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Artikel.objects.annotate(band_list=string_list("band__band_name")),
    )
    schlagwort_list = AnnotationField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        expr=string_list("schlagwort__schlagwort"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    ort_list = AnnotationField(
        attribute="ort_list",
        column_name="Orte",
        expr=string_list("ort___name", sep="; "),
    )
    spielort_list = AnnotationField(
        attribute="spielort_list",
        column_name="Spielorte",
        expr=string_list("spielort__name"),
    )
    veranstaltung_list = AnnotationField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        expr=string_list("veranstaltung__name"),
    )
    person_list = AnnotationField(
        attribute="person_list",
        column_name="Personen",
        expr=string_list("person___name"),
    )

    class Meta:
        model = _models.Artikel
        fields = [
            "id",
            "ausgabe",
            "schlagzeile",
            "seite",
            "seitenumfang",
            "zusammenfassung",
            "autor_list",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "ausgabe",
            "schlagzeile",
            "seite",
            "seitenumfang",
            "zusammenfassung",
            "autor_list",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "beschreibung",
        ]
        widgets = {"ausgabe": {"field": "_name"}}
        select_related = ["ausgabe"]


class BandResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    bandalias_list = AnnotationField(
        attribute="bandalias_list",
        column_name="Alias",
        expr=string_list("bandalias__alias"),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Band-Mitglieder",
        queryset=_models.Band.objects.annotate(musiker_list=string_list("musiker__kuenstler_name")),
    )
    orte_list = AnnotationField(
        attribute="orte_list",
        column_name="Assoziierte Orte",
        expr=string_list("orte___name", sep="; "),
    )

    class Meta:
        model = _models.Band
        fields = [
            "id",
            "band_name",
            "urls_list",
            "genre_list",
            "bandalias_list",
            "musiker_list",
            "orte_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "band_name",
            "urls_list",
            "genre_list",
            "bandalias_list",
            "musiker_list",
            "orte_list",
            "beschreibung",
        ]


class PlakatResource(MIZResource):
    schlagwort_list = AnnotationField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        expr=string_list("schlagwort__schlagwort"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Plakat.objects.annotate(musiker_list=string_list("musiker__kuenstler_name")),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Plakat.objects.annotate(band_list=string_list("band__band_name")),
    )
    ort_list = AnnotationField(
        attribute="ort_list",
        column_name="Orte",
        expr=string_list("ort___name", sep="; "),
    )
    spielort_list = AnnotationField(
        attribute="spielort_list",
        column_name="Spielorte",
        expr=string_list("spielort__name"),
    )
    veranstaltung_list = AnnotationField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        expr=string_list("veranstaltung__name"),
    )
    person_list = AnnotationField(
        attribute="person_list",
        column_name="Personen",
        expr=string_list("person___name"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Plakat
        fields = [
            "id",
            "titel",
            "size",
            "datum",
            "reihe",
            "schlagwort_list",
            "genre_list",
            "musiker_list",
            "band_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "titel",
            "size",
            "datum",
            "reihe",
            "schlagwort_list",
            "genre_list",
            "musiker_list",
            "band_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"reihe": {"field": "name"}}
        select_related = ["reihe"]


class BuchResource(MIZResource):
    autor_list = AnnotationField(
        attribute="autor_list",
        column_name="Autoren",
        expr=string_list("autor___name"),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Buch.objects.annotate(musiker_list=string_list("musiker__kuenstler_name")),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Buch.objects.annotate(band_list=string_list("band__band_name")),
    )
    schlagwort_list = AnnotationField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        expr=string_list("schlagwort__schlagwort"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    ort_list = AnnotationField(
        attribute="ort_list",
        column_name="Orte",
        expr=string_list("ort___name", sep="; "),
    )
    spielort_list = AnnotationField(
        attribute="spielort_list",
        column_name="Spielorte",
        expr=string_list("spielort__name"),
    )
    veranstaltung_list = AnnotationField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        expr=string_list("veranstaltung__name"),
    )
    person_list = AnnotationField(
        attribute="person_list",
        column_name="Personen",
        expr=string_list("person___name"),
    )
    herausgeber_list = AnnotationField(
        attribute="herausgeber_list",
        column_name="Herausgeber",
        expr=string_list("herausgeber__herausgeber"),
    )
    verlag_list = AnnotationField(
        attribute="verlag_list",
        column_name="Verlage",
        expr=string_list("verlag__verlag_name"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Buch
        fields = [
            "id",
            "titel",
            "seitenumfang",
            "jahr",
            "auflage",
            "schriftenreihe",
            "buchband",
            "is_buchband",
            "ISBN",
            "EAN",
            "sprache",
            "titel_orig",
            "jahr_orig",
            "autor_list",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "herausgeber_list",
            "verlag_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "titel",
            "seitenumfang",
            "jahr",
            "auflage",
            "schriftenreihe",
            "buchband",
            "is_buchband",
            "ISBN",
            "EAN",
            "sprache",
            "titel_orig",
            "jahr_orig",
            "autor_list",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "herausgeber_list",
            "verlag_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"schriftenreihe": {"field": "name"}, "buchband": {"field": "titel"}}
        select_related = ["schriftenreihe", "buchband"]


class GenreResource(MIZResource):
    genrealias_list = AnnotationField(
        attribute="genrealias_list",
        column_name="Alias",
        expr=string_list("genrealias__alias"),
    )

    class Meta:
        model = _models.Genre
        fields = ["id", "genre", "genrealias_list"]
        export_order = ["id", "genre", "genrealias_list"]


class MagazinResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    verlag_list = AnnotationField(
        attribute="verlag_list",
        column_name="Verlage",
        expr=string_list("verlag__verlag_name"),
    )
    herausgeber_list = AnnotationField(
        attribute="herausgeber_list",
        column_name="Herausgeber",
        expr=string_list("herausgeber__herausgeber"),
    )
    orte_list = AnnotationField(
        attribute="orte_list",
        column_name="Assoziierte Orte",
        expr=string_list("orte___name", sep="; "),
    )

    class Meta:
        model = _models.Magazin
        fields = [
            "id",
            "magazin_name",
            "ausgaben_merkmal",
            "fanzine",
            "issn",
            "urls_list",
            "genre_list",
            "verlag_list",
            "herausgeber_list",
            "orte_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "magazin_name",
            "ausgaben_merkmal",
            "fanzine",
            "issn",
            "urls_list",
            "genre_list",
            "verlag_list",
            "herausgeber_list",
            "orte_list",
            "beschreibung",
        ]


class MusikerResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    musikeralias_list = AnnotationField(
        attribute="musikeralias_list",
        column_name="Alias",
        expr=string_list("musikeralias__alias"),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands (Mitglied)",
        queryset=_models.Musiker.objects.annotate(band_list=string_list("band__band_name")),
    )
    orte_list = AnnotationField(
        attribute="orte_list",
        column_name="Assoziierte Orte",
        expr=string_list("orte___name", sep="; "),
    )
    instrument_list = AnnotationField(
        attribute="instrument_list",
        column_name="Instrumente",
        expr=string_list("instrument__instrument"),
    )

    class Meta:
        model = _models.Musiker
        fields = [
            "id",
            "kuenstler_name",
            "person",
            "urls_list",
            "genre_list",
            "musikeralias_list",
            "band_list",
            "orte_list",
            "instrument_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "kuenstler_name",
            "person",
            "urls_list",
            "genre_list",
            "musikeralias_list",
            "band_list",
            "orte_list",
            "instrument_list",
            "beschreibung",
        ]
        widgets = {"person": {"field": "_name"}}
        select_related = ["person"]


class PersonResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    orte_list = AnnotationField(
        attribute="orte_list",
        column_name="Assoziierte Orte",
        expr=string_list("orte___name", sep="; "),
    )

    class Meta:
        model = _models.Person
        fields = ["id", "vorname", "nachname", "urls_list", "orte_list", "beschreibung"]
        export_order = ["id", "vorname", "nachname", "urls_list", "orte_list", "beschreibung"]


class SchlagwortResource(MIZResource):
    schlagwortalias_list = AnnotationField(
        attribute="schlagwortalias_list",
        column_name="Alias",
        expr=string_list("schlagwortalias__alias"),
    )

    class Meta:
        model = _models.Schlagwort
        fields = ["id", "schlagwort", "schlagwortalias_list"]
        export_order = ["id", "schlagwort", "schlagwortalias_list"]


class SpielortResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    spielortalias_list = AnnotationField(
        attribute="spielortalias_list",
        column_name="Alias",
        expr=string_list("spielortalias__alias"),
    )

    class Meta:
        model = _models.Spielort
        fields = ["id", "name", "ort", "urls_list", "spielortalias_list", "beschreibung"]
        export_order = ["id", "name", "ort", "urls_list", "spielortalias_list", "beschreibung"]
        widgets = {"ort": {"field": "_name"}}
        select_related = ["ort"]


class VeranstaltungResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    veranstaltungalias_list = AnnotationField(
        attribute="veranstaltungalias_list",
        column_name="Alias",
        expr=string_list("veranstaltungalias__alias"),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Veranstaltung.objects.annotate(musiker_list=string_list("musiker__kuenstler_name")),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Veranstaltung.objects.annotate(band_list=string_list("band__band_name")),
    )
    schlagwort_list = AnnotationField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        expr=string_list("schlagwort__schlagwort"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    person_list = AnnotationField(
        attribute="person_list",
        column_name="Personen",
        expr=string_list("person___name"),
    )

    class Meta:
        model = _models.Veranstaltung
        fields = [
            "id",
            "name",
            "datum",
            "spielort",
            "reihe",
            "urls_list",
            "veranstaltungalias_list",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "person_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "name",
            "datum",
            "spielort",
            "reihe",
            "urls_list",
            "veranstaltungalias_list",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "person_list",
            "beschreibung",
        ]
        widgets = {"spielort": {"field": "name"}, "reihe": {"field": "name"}}
        select_related = ["spielort", "reihe"]


class VerlagResource(MIZResource):
    class Meta:
        model = _models.Verlag
        fields = ["id", "verlag_name", "sitz"]
        export_order = ["id", "verlag_name", "sitz"]
        widgets = {"sitz": {"field": "_name"}}
        select_related = ["sitz"]


class VideoResource(MIZResource):
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Video.objects.annotate(musiker_list=string_list("musiker__kuenstler_name")),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Video.objects.annotate(band_list=string_list("band__band_name")),
    )
    schlagwort_list = AnnotationField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        expr=string_list("schlagwort__schlagwort"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    ort_list = AnnotationField(
        attribute="ort_list",
        column_name="Orte",
        expr=string_list("ort___name", sep="; "),
    )
    spielort_list = AnnotationField(
        attribute="spielort_list",
        column_name="Spielorte",
        expr=string_list("spielort__name"),
    )
    veranstaltung_list = AnnotationField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        expr=string_list("veranstaltung__name"),
    )
    person_list = AnnotationField(
        attribute="person_list",
        column_name="Personen",
        expr=string_list("person___name"),
    )
    ausgabe_list = AnnotationField(
        attribute="ausgabe_list",
        column_name="Ausgaben",
        expr=string_list("ausgabe___name"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Video
        fields = [
            "id",
            "titel",
            "laufzeit",
            "jahr",
            "original",
            "quelle",
            "medium",
            "medium_qty",
            "release_id",
            "discogs_url",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "ausgabe_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "titel",
            "laufzeit",
            "jahr",
            "original",
            "quelle",
            "medium",
            "medium_qty",
            "release_id",
            "discogs_url",
            "musiker_list",
            "band_list",
            "schlagwort_list",
            "genre_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "ausgabe_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"medium": {"field": "medium"}}
        select_related = ["medium"]


class OrtResource(MIZResource):
    class Meta:
        model = _models.Ort
        fields = ["id", "stadt", "land", "bland"]
        export_order = ["id", "stadt", "land", "bland"]
        widgets = {"land": {"field": "land_name"}, "bland": {"field": "bland_name"}}
        select_related = ["land", "bland"]


class BestandResource(MIZResource):
    class Meta:
        model = _models.Bestand
        fields = [
            "signatur",
            "lagerort",
            "anmerkungen",
            "provenienz",
            "audio",
            "ausgabe",
            "brochure",
            "buch",
            "dokument",
            "foto",
            "memorabilien",
            "plakat",
            "technik",
            "video",
        ]
        export_order = [
            "signatur",
            "lagerort",
            "anmerkungen",
            "provenienz",
            "audio",
            "ausgabe",
            "brochure",
            "buch",
            "dokument",
            "foto",
            "memorabilien",
            "plakat",
            "technik",
            "video",
        ]
        widgets = {
            "lagerort": {"field": "_name"},
            "provenienz": {"field": "geber__name"},
            "audio": {"field": "titel"},
            "ausgabe": {"field": "_name"},
            "brochure": {"field": "titel"},
            "buch": {"field": "titel"},
            "dokument": {"field": "titel"},
            "foto": {"field": "titel"},
            "memorabilien": {"field": "titel"},
            "plakat": {"field": "titel"},
            "technik": {"field": "titel"},
            "video": {"field": "titel"},
        }
        select_related = [
            "lagerort",
            "provenienz",
            "audio",
            "ausgabe",
            "brochure",
            "buch",
            "dokument",
            "foto",
            "memorabilien",
            "plakat",
            "technik",
            "video",
        ]


class InstrumentResource(MIZResource):
    class Meta:
        model = _models.Instrument
        fields = ["id", "instrument", "kuerzel"]
        export_order = ["id", "instrument", "kuerzel"]


class HerausgeberResource(MIZResource):
    class Meta:
        model = _models.Herausgeber
        fields = ["id", "herausgeber"]
        export_order = ["id", "herausgeber"]


class BrochureResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    jahre_list = AnnotationField(
        attribute="jahre_list",
        column_name="Jahre",
        expr=string_list("jahre__jahr"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    schlagwort_list = AnnotationField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        expr=string_list("schlagwort__schlagwort"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Brochure
        fields = [
            "basebrochure_ptr",
            "titel",
            "zusammenfassung",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "schlagwort_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "basebrochure_ptr",
            "titel",
            "zusammenfassung",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "schlagwort_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"ausgabe": {"field": "_name"}}
        select_related = ["ausgabe"]


class KatalogResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    jahre_list = AnnotationField(
        attribute="jahre_list",
        column_name="Jahre",
        expr=string_list("jahre__jahr"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Katalog
        fields = [
            "basebrochure_ptr",
            "titel",
            "art",
            "zusammenfassung",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "basebrochure_ptr",
            "titel",
            "art",
            "zusammenfassung",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"ausgabe": {"field": "_name"}}
        select_related = ["ausgabe"]


class KalenderResource(MIZResource):
    urls_list = AnnotationField(
        attribute="urls_list",
        column_name="Webseiten",
        expr=string_list("urls__url"),
    )
    jahre_list = AnnotationField(
        attribute="jahre_list",
        column_name="Jahre",
        expr=string_list("jahre__jahr"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    spielort_list = AnnotationField(
        attribute="spielort_list",
        column_name="Spielorte",
        expr=string_list("spielort__name"),
    )
    veranstaltung_list = AnnotationField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        expr=string_list("veranstaltung__name"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Kalender
        fields = [
            "basebrochure_ptr",
            "titel",
            "zusammenfassung",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "spielort_list",
            "veranstaltung_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "basebrochure_ptr",
            "titel",
            "zusammenfassung",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "spielort_list",
            "veranstaltung_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"ausgabe": {"field": "_name"}}
        select_related = ["ausgabe"]


class FotoResource(MIZResource):
    schlagwort_list = AnnotationField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        expr=string_list("schlagwort__schlagwort"),
    )
    genre_list = AnnotationField(
        attribute="genre_list",
        column_name="Genres",
        expr=string_list("genre__genre"),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Foto.objects.annotate(musiker_list=string_list("musiker__kuenstler_name")),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Foto.objects.annotate(band_list=string_list("band__band_name")),
    )
    ort_list = AnnotationField(
        attribute="ort_list",
        column_name="Orte",
        expr=string_list("ort___name", sep="; "),
    )
    spielort_list = AnnotationField(
        attribute="spielort_list",
        column_name="Spielorte",
        expr=string_list("spielort__name"),
    )
    veranstaltung_list = AnnotationField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        expr=string_list("veranstaltung__name"),
    )
    person_list = AnnotationField(
        attribute="person_list",
        column_name="Personen",
        expr=string_list("person___name"),
    )
    bestand_list = AnnotationField(
        attribute="bestand_list",
        column_name="Bestände",
        expr=string_list("bestand__lagerort___name"),
    )

    class Meta:
        model = _models.Foto
        fields = [
            "id",
            "titel",
            "size",
            "typ",
            "farbe",
            "datum",
            "reihe",
            "owner",
            "schlagwort_list",
            "genre_list",
            "musiker_list",
            "band_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "titel",
            "size",
            "typ",
            "farbe",
            "datum",
            "reihe",
            "owner",
            "schlagwort_list",
            "genre_list",
            "musiker_list",
            "band_list",
            "ort_list",
            "spielort_list",
            "veranstaltung_list",
            "person_list",
            "bestand_list",
            "beschreibung",
        ]
        widgets = {"reihe": {"field": "name"}}
        select_related = ["reihe"]


class PlattenfirmaResource(MIZResource):
    class Meta:
        model = _models.Plattenfirma
        fields = ["id", "name"]
        export_order = ["id", "name"]


class LagerortResource(MIZResource):
    class Meta:
        model = _models.Lagerort
        fields = ["id", "ort", "raum", "regal", "fach", "ordner"]
        export_order = ["id", "ort", "raum", "regal", "fach", "ordner"]


class GeberResource(MIZResource):
    class Meta:
        model = _models.Geber
        fields = ["id", "name"]
        export_order = ["id", "name"]


class ProvenienzResource(MIZResource):
    class Meta:
        model = _models.Provenienz
        fields = ["id", "typ", "geber"]
        export_order = ["id", "typ", "geber"]
        widgets = {"geber": {"field": "name"}}
        select_related = ["geber"]


class SchriftenreiheResource(MIZResource):
    class Meta:
        model = _models.Schriftenreihe
        fields = ["id", "name"]
        export_order = ["id", "name"]


class BildreiheResource(MIZResource):
    class Meta:
        model = _models.Bildreihe
        fields = ["id", "name"]
        export_order = ["id", "name"]


class VeranstaltungsreiheResource(MIZResource):
    class Meta:
        model = _models.Veranstaltungsreihe
        fields = ["id", "name"]
        export_order = ["id", "name"]


class VideoMediumResource(MIZResource):
    class Meta:
        model = _models.VideoMedium
        fields = ["id", "medium"]
        export_order = ["id", "medium"]


class AudioMediumResource(MIZResource):
    class Meta:
        model = _models.AudioMedium
        fields = ["id", "medium"]
        export_order = ["id", "medium"]
