from import_export.fields import Field

from dbentry import models as _models
from dbentry.export.models import MIZResource
from dbentry.utils.query import string_list


class AudioResource(MIZResource):
    musiker_list = Field(attribute="musiker_list", column_name="Musiker")
    band_list = Field(attribute="band_list", column_name="Bands")
    schlagwort_list = Field(attribute="schlagwort_list", column_name="Schlagwörter")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    ort_list = Field(attribute="ort_list", column_name="Orte")
    spielort_list = Field(attribute="spielort_list", column_name="Spielorte")
    veranstaltung_list = Field(attribute="veranstaltung_list", column_name="Veranstaltungen")
    person_list = Field(attribute="person_list", column_name="Personen")
    plattenfirma_list = Field(attribute="plattenfirma_list", column_name="Plattenfirmen")
    ausgabe_list = Field(attribute="ausgabe_list", column_name="Ausgaben")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

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
        annotations = {
            "musiker_list": string_list("musiker__kuenstler_name"),
            "band_list": string_list("band__band_name"),
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "genre_list": string_list("genre__genre"),
            "ort_list": string_list("ort___name", sep="; "),
            "spielort_list": string_list("spielort__name"),
            "veranstaltung_list": string_list("veranstaltung__name"),
            "person_list": string_list("person___name"),
            "plattenfirma_list": string_list("plattenfirma__name"),
            "ausgabe_list": string_list("ausgabe___name"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"land_pressung": {"field": "land_name"}, "medium": {"field": "medium"}}


class AusgabeResource(MIZResource):
    ausgabenum_list = Field(attribute="ausgabenum_list", column_name="Ausgabennummern")
    ausgabemonat_list = Field(attribute="ausgabemonat_list", column_name="Monate")
    ausgabelnum_list = Field(attribute="ausgabelnum_list", column_name="Laufende Nummer")
    ausgabejahr_list = Field(attribute="ausgabejahr_list", column_name="erschienen im Jahr")
    audio_list = Field(attribute="audio_list", column_name="Audio Materialien")
    video_list = Field(attribute="video_list", column_name="Video Materialien")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

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
        annotations = {
            "ausgabenum_list": string_list("ausgabenum__"),
            "ausgabemonat_list": string_list("ausgabemonat__"),
            "ausgabelnum_list": string_list("ausgabelnum__"),
            "ausgabejahr_list": string_list("ausgabejahr__"),
            "audio_list": string_list("audio__titel"),
            "video_list": string_list("video__titel"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"magazin": {"field": "magazin_name"}}


class AutorResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    magazin_list = Field(attribute="magazin_list", column_name="Magazine")

    class Meta:
        model = _models.Autor
        fields = ["id", "person", "kuerzel", "urls_list", "magazin_list", "beschreibung"]
        export_order = ["id", "person", "kuerzel", "urls_list", "magazin_list", "beschreibung"]
        annotations = {"urls_list": string_list("urls__url"), "magazin_list": string_list("magazin__magazin_name")}
        widgets = {"person": {"field": "_name"}}


class ArtikelResource(MIZResource):
    autor_list = Field(attribute="autor_list", column_name="Autoren")
    musiker_list = Field(attribute="musiker_list", column_name="Musiker")
    band_list = Field(attribute="band_list", column_name="Bands")
    schlagwort_list = Field(attribute="schlagwort_list", column_name="Schlagwörter")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    ort_list = Field(attribute="ort_list", column_name="Orte")
    spielort_list = Field(attribute="spielort_list", column_name="Spielorte")
    veranstaltung_list = Field(attribute="veranstaltung_list", column_name="Veranstaltungen")
    person_list = Field(attribute="person_list", column_name="Personen")

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
        annotations = {
            "autor_list": string_list("autor___name"),
            "musiker_list": string_list("musiker__kuenstler_name"),
            "band_list": string_list("band__band_name"),
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "genre_list": string_list("genre__genre"),
            "ort_list": string_list("ort___name", sep="; "),
            "spielort_list": string_list("spielort__name"),
            "veranstaltung_list": string_list("veranstaltung__name"),
            "person_list": string_list("person___name"),
        }
        widgets = {"ausgabe": {"field": "_name"}}


class BandResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    bandalias_list = Field(attribute="bandalias_list", column_name="Alias")
    musiker_list = Field(attribute="musiker_list", column_name="Band-Mitglieder")
    orte_list = Field(attribute="orte_list", column_name="Assoziierte Orte")

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
        annotations = {
            "urls_list": string_list("urls__url"),
            "genre_list": string_list("genre__genre"),
            "bandalias_list": string_list("bandalias__alias"),
            "musiker_list": string_list("musiker__kuenstler_name"),
            "orte_list": string_list("orte___name", sep="; "),
        }


class PlakatResource(MIZResource):
    schlagwort_list = Field(attribute="schlagwort_list", column_name="Schlagwörter")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    musiker_list = Field(attribute="musiker_list", column_name="Musiker")
    band_list = Field(attribute="band_list", column_name="Bands")
    ort_list = Field(attribute="ort_list", column_name="Orte")
    spielort_list = Field(attribute="spielort_list", column_name="Spielorte")
    veranstaltung_list = Field(attribute="veranstaltung_list", column_name="Veranstaltungen")
    person_list = Field(attribute="person_list", column_name="Personen")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

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
        annotations = {
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "genre_list": string_list("genre__genre"),
            "musiker_list": string_list("musiker__kuenstler_name"),
            "band_list": string_list("band__band_name"),
            "ort_list": string_list("ort___name", sep="; "),
            "spielort_list": string_list("spielort__name"),
            "veranstaltung_list": string_list("veranstaltung__name"),
            "person_list": string_list("person___name"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"reihe": {"field": "name"}}


class BuchResource(MIZResource):
    autor_list = Field(attribute="autor_list", column_name="Autoren")
    musiker_list = Field(attribute="musiker_list", column_name="Musiker")
    band_list = Field(attribute="band_list", column_name="Bands")
    schlagwort_list = Field(attribute="schlagwort_list", column_name="Schlagwörter")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    ort_list = Field(attribute="ort_list", column_name="Orte")
    spielort_list = Field(attribute="spielort_list", column_name="Spielorte")
    veranstaltung_list = Field(attribute="veranstaltung_list", column_name="Veranstaltungen")
    person_list = Field(attribute="person_list", column_name="Personen")
    herausgeber_list = Field(attribute="herausgeber_list", column_name="Herausgeber")
    verlag_list = Field(attribute="verlag_list", column_name="Verlage")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

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
        annotations = {
            "autor_list": string_list("autor___name"),
            "musiker_list": string_list("musiker__kuenstler_name"),
            "band_list": string_list("band__band_name"),
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "genre_list": string_list("genre__genre"),
            "ort_list": string_list("ort___name", sep="; "),
            "spielort_list": string_list("spielort__name"),
            "veranstaltung_list": string_list("veranstaltung__name"),
            "person_list": string_list("person___name"),
            "herausgeber_list": string_list("herausgeber__herausgeber"),
            "verlag_list": string_list("verlag__verlag_name"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"schriftenreihe": {"field": "name"}, "buchband": {"field": "titel"}}


class GenreResource(MIZResource):
    genrealias_list = Field(attribute="genrealias_list", column_name="Alias")

    class Meta:
        model = _models.Genre
        fields = ["id", "genre", "genrealias_list"]
        export_order = ["id", "genre", "genrealias_list"]
        annotations = {"genrealias_list": string_list("genrealias__alias")}


class MagazinResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    verlag_list = Field(attribute="verlag_list", column_name="Verlage")
    herausgeber_list = Field(attribute="herausgeber_list", column_name="Herausgeber")
    orte_list = Field(attribute="orte_list", column_name="Assoziierte Orte")

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
        annotations = {
            "urls_list": string_list("urls__url"),
            "genre_list": string_list("genre__genre"),
            "verlag_list": string_list("verlag__verlag_name"),
            "herausgeber_list": string_list("herausgeber__herausgeber"),
            "orte_list": string_list("orte___name", sep="; "),
        }


class MusikerResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    musikeralias_list = Field(attribute="musikeralias_list", column_name="Alias")
    band_list = Field(attribute="band_list", column_name="Bands (Mitglied)")
    orte_list = Field(attribute="orte_list", column_name="Assoziierte Orte")
    instrument_list = Field(attribute="instrument_list", column_name="Instrumente")

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
        annotations = {
            "urls_list": string_list("urls__url"),
            "genre_list": string_list("genre__genre"),
            "musikeralias_list": string_list("musikeralias__alias"),
            "band_list": string_list("band__band_name"),
            "orte_list": string_list("orte___name", sep="; "),
            "instrument_list": string_list("instrument__instrument"),
        }
        widgets = {"person": {"field": "_name"}}


class PersonResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    orte_list = Field(attribute="orte_list", column_name="Assoziierte Orte")

    class Meta:
        model = _models.Person
        fields = ["id", "vorname", "nachname", "urls_list", "orte_list", "beschreibung"]
        export_order = ["id", "vorname", "nachname", "urls_list", "orte_list", "beschreibung"]
        annotations = {"urls_list": string_list("urls__url"), "orte_list": string_list("orte___name", sep="; ")}


class SchlagwortResource(MIZResource):
    schlagwortalias_list = Field(attribute="schlagwortalias_list", column_name="Alias")

    class Meta:
        model = _models.Schlagwort
        fields = ["id", "schlagwort", "schlagwortalias_list"]
        export_order = ["id", "schlagwort", "schlagwortalias_list"]
        annotations = {"schlagwortalias_list": string_list("schlagwortalias__alias")}


class SpielortResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    spielortalias_list = Field(attribute="spielortalias_list", column_name="Alias")

    class Meta:
        model = _models.Spielort
        fields = ["id", "name", "ort", "urls_list", "spielortalias_list", "beschreibung"]
        export_order = ["id", "name", "ort", "urls_list", "spielortalias_list", "beschreibung"]
        annotations = {"urls_list": string_list("urls__url"), "spielortalias_list": string_list("spielortalias__alias")}
        widgets = {"ort": {"field": "_name"}}


class VeranstaltungResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    veranstaltungalias_list = Field(attribute="veranstaltungalias_list", column_name="Alias")
    musiker_list = Field(attribute="musiker_list", column_name="Musiker")
    band_list = Field(attribute="band_list", column_name="Bands")
    schlagwort_list = Field(attribute="schlagwort_list", column_name="Schlagwörter")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    person_list = Field(attribute="person_list", column_name="Personen")

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
        annotations = {
            "urls_list": string_list("urls__url"),
            "veranstaltungalias_list": string_list("veranstaltungalias__alias"),
            "musiker_list": string_list("musiker__kuenstler_name"),
            "band_list": string_list("band__band_name"),
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "genre_list": string_list("genre__genre"),
            "person_list": string_list("person___name"),
        }
        widgets = {"spielort": {"field": "name"}, "reihe": {"field": "name"}}


class VerlagResource(MIZResource):
    class Meta:
        model = _models.Verlag
        fields = ["id", "verlag_name", "sitz"]
        export_order = ["id", "verlag_name", "sitz"]
        widgets = {"sitz": {"field": "_name"}}


class VideoResource(MIZResource):
    musiker_list = Field(attribute="musiker_list", column_name="Musiker")
    band_list = Field(attribute="band_list", column_name="Bands")
    schlagwort_list = Field(attribute="schlagwort_list", column_name="Schlagwörter")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    ort_list = Field(attribute="ort_list", column_name="Orte")
    spielort_list = Field(attribute="spielort_list", column_name="Spielorte")
    veranstaltung_list = Field(attribute="veranstaltung_list", column_name="Veranstaltungen")
    person_list = Field(attribute="person_list", column_name="Personen")
    ausgabe_list = Field(attribute="ausgabe_list", column_name="Ausgaben")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

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
        annotations = {
            "musiker_list": string_list("musiker__kuenstler_name"),
            "band_list": string_list("band__band_name"),
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "genre_list": string_list("genre__genre"),
            "ort_list": string_list("ort___name", sep="; "),
            "spielort_list": string_list("spielort__name"),
            "veranstaltung_list": string_list("veranstaltung__name"),
            "person_list": string_list("person___name"),
            "ausgabe_list": string_list("ausgabe___name"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"medium": {"field": "medium"}}


class OrtResource(MIZResource):
    class Meta:
        model = _models.Ort
        fields = ["id", "stadt", "land", "bland"]
        export_order = ["id", "stadt", "land", "bland"]
        widgets = {"land": {"field": "land_name"}, "bland": {"field": "bland_name"}}


class BestandResource(MIZResource):
    class Meta:
        model = _models.Bestand
        fields = [
            "id",
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
            "id",
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
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    jahre_list = Field(attribute="jahre_list", column_name="Jahre")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    schlagwort_list = Field(attribute="schlagwort_list", column_name="Schlagwörter")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

    class Meta:
        model = _models.Brochure
        fields = [
            "id",
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
            "id",
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
        annotations = {
            "urls_list": string_list("urls__url"),
            "jahre_list": string_list("jahre__jahr"),
            "genre_list": string_list("genre__genre"),
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"ausgabe": {"field": "_name"}}


class KatalogResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    jahre_list = Field(attribute="jahre_list", column_name="Jahre")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

    class Meta:
        model = _models.Katalog
        fields = [
            "id",
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
            "id",
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
        annotations = {
            "urls_list": string_list("urls__url"),
            "jahre_list": string_list("jahre__jahr"),
            "genre_list": string_list("genre__genre"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"ausgabe": {"field": "_name"}}


class KalenderResource(MIZResource):
    urls_list = Field(attribute="urls_list", column_name="Webseiten")
    jahre_list = Field(attribute="jahre_list", column_name="Jahre")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    spielort_list = Field(attribute="spielort_list", column_name="Spielorte")
    veranstaltung_list = Field(attribute="veranstaltung_list", column_name="Veranstaltungen")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

    class Meta:
        model = _models.Kalender
        fields = [
            "id",
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
            "id",
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
        annotations = {
            "urls_list": string_list("urls__url"),
            "jahre_list": string_list("jahre__jahr"),
            "genre_list": string_list("genre__genre"),
            "spielort_list": string_list("spielort__name"),
            "veranstaltung_list": string_list("veranstaltung__name"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"ausgabe": {"field": "_name"}}


class FotoResource(MIZResource):
    schlagwort_list = Field(attribute="schlagwort_list", column_name="Schlagwörter")
    genre_list = Field(attribute="genre_list", column_name="Genres")
    musiker_list = Field(attribute="musiker_list", column_name="Musiker")
    band_list = Field(attribute="band_list", column_name="Bands")
    ort_list = Field(attribute="ort_list", column_name="Orte")
    spielort_list = Field(attribute="spielort_list", column_name="Spielorte")
    veranstaltung_list = Field(attribute="veranstaltung_list", column_name="Veranstaltungen")
    person_list = Field(attribute="person_list", column_name="Personen")
    bestand_list = Field(attribute="bestand_list", column_name="Bestände")

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
        annotations = {
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "genre_list": string_list("genre__genre"),
            "musiker_list": string_list("musiker__kuenstler_name"),
            "band_list": string_list("band__band_name"),
            "ort_list": string_list("ort___name", sep="; "),
            "spielort_list": string_list("spielort__name"),
            "veranstaltung_list": string_list("veranstaltung__name"),
            "person_list": string_list("person___name"),
            "bestand_list": string_list("bestand__lagerort___name"),
        }
        widgets = {"reihe": {"field": "name"}}


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
