from import_export.fields import Field

from dbentry import models as _models
from dbentry.export.base import MIZResource
from dbentry.export.fields import CachedQuerysetField, ChoiceField
from dbentry.utils.query import string_list


class AudioResource(MIZResource):
    land_pressung = Field(attribute="land_pressung__land_name", column_name="Land Pressung")
    medium = Field(attribute="medium__medium", column_name="Speichermedium")
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Audio.objects.annotate(musiker_list=string_list("musiker__kuenstler_name", length=1024)),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Audio.objects.annotate(band_list=string_list("band__band_name", length=1024)),
    )
    schlagwort_list = CachedQuerysetField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        queryset=_models.Audio.objects.annotate(schlagwort_list=string_list("schlagwort__schlagwort", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Audio.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    ort_list = CachedQuerysetField(
        attribute="ort_list",
        column_name="Orte",
        queryset=_models.Audio.objects.annotate(ort_list=string_list("ort___name", sep="; ", length=1024)),
    )
    spielort_list = CachedQuerysetField(
        attribute="spielort_list",
        column_name="Spielorte",
        queryset=_models.Audio.objects.annotate(spielort_list=string_list("spielort__name", length=1024)),
    )
    veranstaltung_list = CachedQuerysetField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        queryset=_models.Audio.objects.annotate(veranstaltung_list=string_list("veranstaltung__name", length=1024)),
    )
    person_list = CachedQuerysetField(
        attribute="person_list",
        column_name="Personen",
        queryset=_models.Audio.objects.annotate(person_list=string_list("person___name", length=1024)),
    )
    plattenfirma_list = CachedQuerysetField(
        attribute="plattenfirma_list",
        column_name="Plattenfirmen",
        queryset=_models.Audio.objects.annotate(plattenfirma_list=string_list("plattenfirma__name", length=1024)),
    )
    ausgabe_list = CachedQuerysetField(
        attribute="ausgabe_list",
        column_name="Ausgaben",
        queryset=_models.Audio.objects.annotate(ausgabe_list=string_list("ausgabe___name", length=1024)),
    )
    # TODO: data only includes ausgabe names, but not the names of magazines,
    #  which makes the column rather useless
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Audio.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
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
        select_related = ["land_pressung", "medium"]


class AusgabeResource(MIZResource):
    magazin = Field(attribute="magazin__magazin_name")
    ausgabenum_list = CachedQuerysetField(
        attribute="ausgabenum_list",
        column_name="Ausgabennummern",
        queryset=_models.Ausgabe.objects.annotate(ausgabenum_list=string_list("ausgabenum__num", length=1024)),
    )
    ausgabemonat_list = CachedQuerysetField(
        attribute="ausgabemonat_list",
        column_name="Monate",
        queryset=_models.Ausgabe.objects.annotate(
            ausgabemonat_list=string_list("ausgabemonat__monat__abk", length=1024)
        ),
    )
    ausgabelnum_list = CachedQuerysetField(
        attribute="ausgabelnum_list",
        column_name="Laufende Nummer",
        queryset=_models.Ausgabe.objects.annotate(ausgabelnum_list=string_list("ausgabelnum__lnum", length=1024)),
    )
    ausgabejahr_list = CachedQuerysetField(
        attribute="ausgabejahr_list",
        column_name="erschienen im Jahr",
        queryset=_models.Ausgabe.objects.annotate(ausgabejahr_list=string_list("ausgabejahr__jahr", length=1024)),
    )
    audio_list = CachedQuerysetField(
        attribute="audio_list",
        column_name="Audio Materialien",
        queryset=_models.Ausgabe.objects.annotate(audio_list=string_list("audio__titel", length=1024)),
    )
    video_list = CachedQuerysetField(
        attribute="video_list",
        column_name="Video Materialien",
        queryset=_models.Ausgabe.objects.annotate(video_list=string_list("video__titel", length=1024)),
    )
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Ausgabe.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
    )

    class Meta:
        model = _models.Ausgabe
        fields = [
            "id",
            "magazin",
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
        select_related = ["magazin"]


class AutorResource(MIZResource):
    person = Field(attribute="person___name", column_name="Person")
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Autor.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    magazin_list = CachedQuerysetField(
        attribute="magazin_list",
        column_name="Magazine",
        queryset=_models.Autor.objects.annotate(magazin_list=string_list("magazin__magazin_name", length=1024)),
    )

    class Meta:
        model = _models.Autor
        fields = ["id", "person", "kuerzel", "urls_list", "magazin_list", "beschreibung"]
        export_order = ["id", "person", "kuerzel", "urls_list", "magazin_list", "beschreibung"]
        select_related = ["person"]


class ArtikelResource(MIZResource):
    magazin = Field(attribute="ausgabe__magazin__magazin_name", column_name="Magazin")
    ausgabe = Field(attribute="ausgabe___name", column_name="Ausgabe")
    autor_list = CachedQuerysetField(
        attribute="autor_list",
        column_name="Autoren",
        queryset=_models.Artikel.objects.annotate(autor_list=string_list("autor___name", length=1024)),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Artikel.objects.annotate(musiker_list=string_list("musiker__kuenstler_name", length=1024)),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Artikel.objects.annotate(band_list=string_list("band__band_name", length=1024)),
    )
    schlagwort_list = CachedQuerysetField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        queryset=_models.Artikel.objects.annotate(schlagwort_list=string_list("schlagwort__schlagwort", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Artikel.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    ort_list = CachedQuerysetField(
        attribute="ort_list",
        column_name="Orte",
        queryset=_models.Artikel.objects.annotate(ort_list=string_list("ort___name", sep="; ", length=1024)),
    )
    spielort_list = CachedQuerysetField(
        attribute="spielort_list",
        column_name="Spielorte",
        queryset=_models.Artikel.objects.annotate(spielort_list=string_list("spielort__name", length=1024)),
    )
    veranstaltung_list = CachedQuerysetField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        queryset=_models.Artikel.objects.annotate(veranstaltung_list=string_list("veranstaltung__name", length=1024)),
    )
    person_list = CachedQuerysetField(
        attribute="person_list",
        column_name="Personen",
        queryset=_models.Artikel.objects.annotate(person_list=string_list("person___name", length=1024)),
    )
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Artikel.objects.annotate(
            bestand_list=string_list("ausgabe__bestand__lagerort___name", length=1024)
        ),
    )

    class Meta:
        model = _models.Artikel
        fields = [
            "id",
            "magazin",
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
            "bestand_list",
            "beschreibung",
        ]
        export_order = [
            "id",
            "magazin",
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
            "bestand_list",
            "beschreibung",
        ]
        select_related = ["ausgabe", "ausgabe__magazin"]


class PlakatResource(MIZResource):
    reihe = Field(attribute="reihe__name", column_name="Bildreihe")
    schlagwort_list = CachedQuerysetField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        queryset=_models.Plakat.objects.annotate(schlagwort_list=string_list("schlagwort__schlagwort", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Plakat.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Plakat.objects.annotate(musiker_list=string_list("musiker__kuenstler_name", length=1024)),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Plakat.objects.annotate(band_list=string_list("band__band_name", length=1024)),
    )
    ort_list = CachedQuerysetField(
        attribute="ort_list",
        column_name="Orte",
        queryset=_models.Plakat.objects.annotate(ort_list=string_list("ort___name", sep="; ", length=1024)),
    )
    spielort_list = CachedQuerysetField(
        attribute="spielort_list",
        column_name="Spielorte",
        queryset=_models.Plakat.objects.annotate(spielort_list=string_list("spielort__name", length=1024)),
    )
    veranstaltung_list = CachedQuerysetField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        queryset=_models.Plakat.objects.annotate(veranstaltung_list=string_list("veranstaltung__name", length=1024)),
    )
    person_list = CachedQuerysetField(
        attribute="person_list",
        column_name="Personen",
        queryset=_models.Plakat.objects.annotate(person_list=string_list("person___name", length=1024)),
    )
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Plakat.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
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
        select_related = ["reihe"]


class BandResource(MIZResource):
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Band.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Band.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    bandalias_list = CachedQuerysetField(
        attribute="bandalias_list",
        column_name="Alias",
        queryset=_models.Band.objects.annotate(bandalias_list=string_list("bandalias__alias", length=1024)),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Band-Mitglieder",
        queryset=_models.Band.objects.annotate(musiker_list=string_list("musiker__kuenstler_name", length=1024)),
    )
    orte_list = CachedQuerysetField(
        attribute="orte_list",
        column_name="Assoziierte Orte",
        queryset=_models.Band.objects.annotate(orte_list=string_list("orte___name", sep="; ", length=1024)),
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


class BuchResource(MIZResource):
    schriftenreihe = Field(attribute="schriftenreihe__name", column_name="Schriftenreihe")
    buchband = Field(attribute="buchband__titel", column_name="Sammelband")
    autor_list = CachedQuerysetField(
        attribute="autor_list",
        column_name="Autoren",
        queryset=_models.Buch.objects.annotate(autor_list=string_list("autor___name", length=1024)),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Buch.objects.annotate(musiker_list=string_list("musiker__kuenstler_name", length=1024)),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Buch.objects.annotate(band_list=string_list("band__band_name", length=1024)),
    )
    schlagwort_list = CachedQuerysetField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        queryset=_models.Buch.objects.annotate(schlagwort_list=string_list("schlagwort__schlagwort", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Buch.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    ort_list = CachedQuerysetField(
        attribute="ort_list",
        column_name="Orte",
        queryset=_models.Buch.objects.annotate(ort_list=string_list("ort___name", sep="; ", length=1024)),
    )
    spielort_list = CachedQuerysetField(
        attribute="spielort_list",
        column_name="Spielorte",
        queryset=_models.Buch.objects.annotate(spielort_list=string_list("spielort__name", length=1024)),
    )
    veranstaltung_list = CachedQuerysetField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        queryset=_models.Buch.objects.annotate(veranstaltung_list=string_list("veranstaltung__name", length=1024)),
    )
    person_list = CachedQuerysetField(
        attribute="person_list",
        column_name="Personen",
        queryset=_models.Buch.objects.annotate(person_list=string_list("person___name", length=1024)),
    )
    herausgeber_list = CachedQuerysetField(
        attribute="herausgeber_list",
        column_name="Herausgeber",
        queryset=_models.Buch.objects.annotate(herausgeber_list=string_list("herausgeber__herausgeber", length=1024)),
    )
    verlag_list = CachedQuerysetField(
        attribute="verlag_list",
        column_name="Verlage",
        queryset=_models.Buch.objects.annotate(verlag_list=string_list("verlag__verlag_name", length=1024)),
    )
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Buch.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
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
        select_related = ["schriftenreihe", "buchband"]


class GenreResource(MIZResource):
    genrealias_list = CachedQuerysetField(
        attribute="genrealias_list",
        column_name="Alias",
        queryset=_models.Genre.objects.annotate(genrealias_list=string_list("genrealias__alias", length=1024)),
    )

    class Meta:
        model = _models.Genre
        fields = ["id", "genre", "genrealias_list"]
        export_order = ["id", "genre", "genrealias_list"]


class MagazinResource(MIZResource):
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Magazin.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Magazin.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    verlag_list = CachedQuerysetField(
        attribute="verlag_list",
        column_name="Verlage",
        queryset=_models.Magazin.objects.annotate(verlag_list=string_list("verlag__verlag_name", length=1024)),
    )
    herausgeber_list = CachedQuerysetField(
        attribute="herausgeber_list",
        column_name="Herausgeber",
        queryset=_models.Magazin.objects.annotate(
            herausgeber_list=string_list("herausgeber__herausgeber", length=1024)
        ),
    )
    orte_list = CachedQuerysetField(
        attribute="orte_list",
        column_name="Assoziierte Orte",
        queryset=_models.Magazin.objects.annotate(orte_list=string_list("orte___name", sep="; ", length=1024)),
    )

    class Meta:
        model = _models.Magazin
        fields = [
            "id",
            "magazin_name",
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
    person = Field(attribute="person___name", column_name="Person")
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Musiker.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Musiker.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    musikeralias_list = CachedQuerysetField(
        attribute="musikeralias_list",
        column_name="Alias",
        queryset=_models.Musiker.objects.annotate(musikeralias_list=string_list("musikeralias__alias", length=1024)),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands (Mitglied)",
        queryset=_models.Musiker.objects.annotate(band_list=string_list("band__band_name", length=1024)),
    )
    orte_list = CachedQuerysetField(
        attribute="orte_list",
        column_name="Assoziierte Orte",
        queryset=_models.Musiker.objects.annotate(orte_list=string_list("orte___name", sep="; ", length=1024)),
    )
    instrument_list = CachedQuerysetField(
        attribute="instrument_list",
        column_name="Instrumente",
        queryset=_models.Musiker.objects.annotate(instrument_list=string_list("instrument__instrument", length=1024)),
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
        select_related = ["person"]


class PersonResource(MIZResource):
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Person.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    orte_list = CachedQuerysetField(
        attribute="orte_list",
        column_name="Assoziierte Orte",
        queryset=_models.Person.objects.annotate(orte_list=string_list("orte___name", sep="; ", length=1024)),
    )

    class Meta:
        model = _models.Person
        fields = ["id", "vorname", "nachname", "urls_list", "orte_list", "beschreibung"]
        export_order = ["id", "vorname", "nachname", "urls_list", "orte_list", "beschreibung"]


class SchlagwortResource(MIZResource):
    schlagwortalias_list = CachedQuerysetField(
        attribute="schlagwortalias_list",
        column_name="Alias",
        queryset=_models.Schlagwort.objects.annotate(
            schlagwortalias_list=string_list("schlagwortalias__alias", length=1024)
        ),
    )

    class Meta:
        model = _models.Schlagwort
        fields = ["id", "schlagwort", "schlagwortalias_list"]
        export_order = ["id", "schlagwort", "schlagwortalias_list"]


class SpielortResource(MIZResource):
    ort = Field(attribute="ort___name", column_name="Ort")
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Spielort.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    spielortalias_list = CachedQuerysetField(
        attribute="spielortalias_list",
        column_name="Alias",
        queryset=_models.Spielort.objects.annotate(spielortalias_list=string_list("spielortalias__alias", length=1024)),
    )

    class Meta:
        model = _models.Spielort
        fields = ["id", "name", "ort", "urls_list", "spielortalias_list", "beschreibung"]
        export_order = ["id", "name", "ort", "urls_list", "spielortalias_list", "beschreibung"]
        select_related = ["ort"]


class VeranstaltungResource(MIZResource):
    spielort = Field(attribute="spielort__name", column_name="Spielort")
    reihe = Field(attribute="reihe__name", column_name="Veranstaltungsreihe")
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Veranstaltung.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    veranstaltungalias_list = CachedQuerysetField(
        attribute="veranstaltungalias_list",
        column_name="Alias",
        queryset=_models.Veranstaltung.objects.annotate(
            veranstaltungalias_list=string_list("veranstaltungalias__alias", length=1024)
        ),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Veranstaltung.objects.annotate(
            musiker_list=string_list("musiker__kuenstler_name", length=1024)
        ),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Veranstaltung.objects.annotate(band_list=string_list("band__band_name", length=1024)),
    )
    schlagwort_list = CachedQuerysetField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        queryset=_models.Veranstaltung.objects.annotate(
            schlagwort_list=string_list("schlagwort__schlagwort", length=1024)
        ),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Veranstaltung.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    person_list = CachedQuerysetField(
        attribute="person_list",
        column_name="Personen",
        queryset=_models.Veranstaltung.objects.annotate(person_list=string_list("person___name", length=1024)),
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
        select_related = ["spielort", "reihe"]


class VerlagResource(MIZResource):
    sitz = Field(attribute="sitz___name", column_name="Sitz")

    class Meta:
        model = _models.Verlag
        fields = ["id", "verlag_name", "sitz"]
        export_order = ["id", "verlag_name", "sitz"]
        select_related = ["sitz"]


class VideoResource(MIZResource):
    medium = Field(attribute="medium__medium", column_name="Speichermedium")
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Video.objects.annotate(musiker_list=string_list("musiker__kuenstler_name", length=1024)),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Video.objects.annotate(band_list=string_list("band__band_name", length=1024)),
    )
    schlagwort_list = CachedQuerysetField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        queryset=_models.Video.objects.annotate(schlagwort_list=string_list("schlagwort__schlagwort", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Video.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    ort_list = CachedQuerysetField(
        attribute="ort_list",
        column_name="Orte",
        queryset=_models.Video.objects.annotate(ort_list=string_list("ort___name", sep="; ", length=1024)),
    )
    spielort_list = CachedQuerysetField(
        attribute="spielort_list",
        column_name="Spielorte",
        queryset=_models.Video.objects.annotate(spielort_list=string_list("spielort__name", length=1024)),
    )
    veranstaltung_list = CachedQuerysetField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        queryset=_models.Video.objects.annotate(veranstaltung_list=string_list("veranstaltung__name", length=1024)),
    )
    person_list = CachedQuerysetField(
        attribute="person_list",
        column_name="Personen",
        queryset=_models.Video.objects.annotate(person_list=string_list("person___name", length=1024)),
    )
    ausgabe_list = CachedQuerysetField(
        attribute="ausgabe_list",
        column_name="Ausgaben",
        queryset=_models.Video.objects.annotate(ausgabe_list=string_list("ausgabe___name", length=1024)),
    )
    # TODO: data only includes ausgabe names, but not the names of magazines,
    #  which makes the column rather useless
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Video.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
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
        select_related = ["medium"]


class OrtResource(MIZResource):
    land = Field(attribute="land__land_name", column_name="Land")
    bland = Field(attribute="bland__bland_name", column_name="Bundesland")

    class Meta:
        model = _models.Ort
        fields = ["id", "stadt", "land", "bland"]
        export_order = ["id", "stadt", "land", "bland"]
        select_related = ["land", "bland"]


class BestandResource(MIZResource):
    lagerort = Field(attribute="lagerort___name", column_name="Lagerort")
    provenienz = Field(attribute="provenienz__geber__name", column_name="Provenienz")
    audio = Field(attribute="audio__titel", column_name="Audio")
    ausgabe = Field(attribute="ausgabe___name", column_name="Ausgabe")
    brochure = Field(attribute="brochure__titel", column_name="Broschüre")
    buch = Field(attribute="buch__titel", column_name="Buch")
    dokument = Field(attribute="dokument__titel", column_name="Dokument")
    foto = Field(attribute="foto__titel", column_name="Foto")
    memorabilien = Field(attribute="memorabilien__titel", column_name="Memorabilien")
    plakat = Field(attribute="plakat__titel", column_name="Plakat")
    technik = Field(attribute="technik__titel", column_name="Technik")
    video = Field(attribute="video__titel", column_name="Video")
    magazin = Field(attribute="ausgabe__magazin__magazin_name", column_name="Magazin")

    class Meta:
        model = _models.Bestand
        fields = [
            "signatur",
            "lagerort",
            "anmerkungen",
            "provenienz",
            "audio",
            "magazin",
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
            "magazin",
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
        select_related = [
            "lagerort",
            "provenienz",
            "audio",
            "ausgabe",
            "ausgabe__magazin",
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
    basebrochure_ptr = Field(attribute="basebrochure_ptr__id", column_name="Id")
    magazin = Field(attribute="ausgabe__magazin__magazin_name", column_name="Magazin")
    ausgabe = Field(attribute="ausgabe___name", column_name="Ausgabe")
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Brochure.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    jahre_list = CachedQuerysetField(
        attribute="jahre_list",
        column_name="Jahre",
        queryset=_models.Brochure.objects.annotate(jahre_list=string_list("jahre__jahr", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Brochure.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    schlagwort_list = CachedQuerysetField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        queryset=_models.Brochure.objects.annotate(schlagwort_list=string_list("schlagwort__schlagwort", length=1024)),
    )
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Brochure.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
    )

    class Meta:
        model = _models.Brochure
        fields = [
            "basebrochure_ptr",
            "titel",
            "zusammenfassung",
            "magazin",
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
            "magazin",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "schlagwort_list",
            "bestand_list",
            "beschreibung",
        ]
        select_related = ["ausgabe", "ausgabe__magazin"]


class KatalogResource(MIZResource):
    basebrochure_ptr = Field(attribute="basebrochure_ptr__id", column_name="Id")
    art = ChoiceField(attribute="art")
    magazin = Field(attribute="ausgabe__magazin__magazin_name", column_name="Magazin")
    ausgabe = Field(attribute="ausgabe___name", column_name="Ausgabe")
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Katalog.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    jahre_list = CachedQuerysetField(
        attribute="jahre_list",
        column_name="Jahre",
        queryset=_models.Katalog.objects.annotate(jahre_list=string_list("jahre__jahr", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Katalog.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Katalog.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
    )

    class Meta:
        model = _models.Katalog
        fields = [
            "basebrochure_ptr",
            "titel",
            "art",
            "zusammenfassung",
            "magazin",
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
            "magazin",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "bestand_list",
            "beschreibung",
        ]
        select_related = ["ausgabe", "ausgabe__magazin"]


class KalenderResource(MIZResource):
    basebrochure_ptr = Field(attribute="basebrochure_ptr__id", column_name="Id")
    magazin = Field(attribute="ausgabe__magazin__magazin_name", column_name="Magazin")
    ausgabe = Field(attribute="ausgabe___name", column_name="Ausgabe")
    urls_list = CachedQuerysetField(
        attribute="urls_list",
        column_name="Weblinks",
        queryset=_models.Kalender.objects.annotate(urls_list=string_list("urls__url", length=1024)),
    )
    jahre_list = CachedQuerysetField(
        attribute="jahre_list",
        column_name="Jahre",
        queryset=_models.Kalender.objects.annotate(jahre_list=string_list("jahre__jahr", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Kalender.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    spielort_list = CachedQuerysetField(
        attribute="spielort_list",
        column_name="Spielorte",
        queryset=_models.Kalender.objects.annotate(spielort_list=string_list("spielort__name", length=1024)),
    )
    veranstaltung_list = CachedQuerysetField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        queryset=_models.Kalender.objects.annotate(veranstaltung_list=string_list("veranstaltung__name", length=1024)),
    )
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Kalender.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
    )

    class Meta:
        model = _models.Kalender
        fields = [
            "basebrochure_ptr",
            "titel",
            "zusammenfassung",
            "magazin",
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
            "magazin",
            "ausgabe",
            "urls_list",
            "jahre_list",
            "genre_list",
            "spielort_list",
            "veranstaltung_list",
            "bestand_list",
            "beschreibung",
        ]
        select_related = ["ausgabe", "ausgabe__magazin"]


class FotoResource(MIZResource):
    typ = ChoiceField(attribute="typ")
    reihe = Field(attribute="reihe__name", column_name="Bildreihe")
    schlagwort_list = CachedQuerysetField(
        attribute="schlagwort_list",
        column_name="Schlagwörter",
        queryset=_models.Foto.objects.annotate(schlagwort_list=string_list("schlagwort__schlagwort", length=1024)),
    )
    genre_list = CachedQuerysetField(
        attribute="genre_list",
        column_name="Genres",
        queryset=_models.Foto.objects.annotate(genre_list=string_list("genre__genre", length=1024)),
    )
    musiker_list = CachedQuerysetField(
        attribute="musiker_list",
        column_name="Musiker",
        queryset=_models.Foto.objects.annotate(musiker_list=string_list("musiker__kuenstler_name", length=1024)),
    )
    band_list = CachedQuerysetField(
        attribute="band_list",
        column_name="Bands",
        queryset=_models.Foto.objects.annotate(band_list=string_list("band__band_name", length=1024)),
    )
    ort_list = CachedQuerysetField(
        attribute="ort_list",
        column_name="Orte",
        queryset=_models.Foto.objects.annotate(ort_list=string_list("ort___name", sep="; ", length=1024)),
    )
    spielort_list = CachedQuerysetField(
        attribute="spielort_list",
        column_name="Spielorte",
        queryset=_models.Foto.objects.annotate(spielort_list=string_list("spielort__name", length=1024)),
    )
    veranstaltung_list = CachedQuerysetField(
        attribute="veranstaltung_list",
        column_name="Veranstaltungen",
        queryset=_models.Foto.objects.annotate(veranstaltung_list=string_list("veranstaltung__name", length=1024)),
    )
    person_list = CachedQuerysetField(
        attribute="person_list",
        column_name="Personen",
        queryset=_models.Foto.objects.annotate(person_list=string_list("person___name", length=1024)),
    )
    bestand_list = CachedQuerysetField(
        attribute="bestand_list",
        column_name="Bestände",
        queryset=_models.Foto.objects.annotate(bestand_list=string_list("bestand__lagerort___name", length=1024)),
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
    geber = Field(attribute="geber__name", column_name="Geber")

    class Meta:
        model = _models.Provenienz
        fields = ["id", "typ", "geber"]
        export_order = ["id", "typ", "geber"]
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
