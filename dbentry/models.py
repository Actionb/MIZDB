# TODO: Semantik buch.buchband: Einzelbänder/Aufsätze: Teile eines Buchbandes
from typing import Optional

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Count, Exists, OuterRef, Subquery

import dbentry.m2m as _m2m
from dbentry.base.models import AbstractJahrModel, AbstractURLModel, BaseAliasModel, BaseModel, ComputedNameModel
from dbentry.fields import EANField, ISBNField, ISSNField, PartialDateField, YearField
from dbentry.fts.fields import SearchVectorField, WeightedColumn
from dbentry.fts.query import SIMPLE, STEMMING
from dbentry.query import AusgabeQuerySet, AudioQuerySet
from dbentry.utils.models import get_model_fields, get_model_relations
from dbentry.utils.query import array_to_string, limit, string_list, to_array
from dbentry.utils.text import concat_limit

BESTAND_MODEL_NAME = "dbentry.Bestand"  # TODO: move to models.py


# TODO: use Func(<concatenated array>, Value(50), function="left") in place of
#  "concat_limit()"


class Person(ComputedNameModel):
    vorname = models.CharField(max_length=200, blank=True)
    nachname = models.CharField(max_length=200)

    gnd_id = models.CharField("Normdatei ID", max_length=20, blank=True)
    gnd_name = models.CharField("Normdatei Name", max_length=200, blank=True)
    dnb_url = models.URLField(
        "Link DNB", blank=True, help_text="Adresse zur Seite dieser Person in der Deutschen Nationalbibliothek."
    )
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. der Person")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    orte = models.ManyToManyField("Ort")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("_name", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_composing_fields = ["vorname", "nachname"]

    class Meta(ComputedNameModel.Meta):
        verbose_name = "Person"
        verbose_name_plural = "Personen"

    @classmethod
    def _get_name(cls, **data: tuple) -> str:
        """
        Construct a name from the data given.

        Args:
             **data: mapping of field_path: tuple of values provided by
              MIZQuerySet.values_dict

        Returns:
             a name in the format '{vorname} {nachname}'
        """
        vorname = nachname = ""
        if "vorname" in data:
            vorname = data["vorname"][0]
        if "nachname" in data:
            nachname = data["nachname"][0]
        if vorname or nachname:
            return "{} {}".format(vorname, nachname).strip()
        # noinspection PyUnresolvedReferences
        opts = cls._meta
        return cls._name_default % {"verbose_name": opts.verbose_name}

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "is_musiker": Exists(Musiker.objects.only("id").filter(person_id=OuterRef("id"))),
            "is_autor": Exists(Autor.objects.only("id").filter(person_id=OuterRef("id"))),
            "orte_list": string_list("orte___name", sep="; "),
        }


class PersonURL(AbstractURLModel):
    # TODO: field name is wrong
    brochure = models.ForeignKey("Person", models.CASCADE, related_name="urls")


class Musiker(BaseModel):
    kuenstler_name = models.CharField("Künstlername", max_length=200)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Musikers")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    person = models.ForeignKey("Person", models.SET_NULL, null=True, blank=True)

    genre = models.ManyToManyField("Genre")
    instrument = models.ManyToManyField("Instrument")
    orte = models.ManyToManyField("Ort")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("kuenstler_name", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    create_field = "kuenstler_name"
    name_field = "kuenstler_name"
    related_search_vectors = [("musikeralias___fts", SIMPLE), ("person___fts", SIMPLE)]

    class Meta(BaseModel.Meta):
        verbose_name = "Musiker"
        verbose_name_plural = "Musiker"
        ordering = ["kuenstler_name"]

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "band_list": string_list("band__band_name"),
            "genre_list": string_list("genre__genre"),
            "orte_list": string_list("orte___name", sep="; "),
            "alias_list": string_list("musikeralias__alias"),
        }


class MusikerAlias(BaseAliasModel):
    parent = models.ForeignKey("Musiker", models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("alias", "B", SIMPLE),
        ]
    )


class MusikerURL(AbstractURLModel):
    # TODO: field name is wrong
    brochure = models.ForeignKey("Musiker", models.CASCADE, related_name="urls")


class Genre(BaseModel):
    genre = models.CharField("Genre", max_length=100, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("genre", "A", SIMPLE),
        ]
    )

    create_field = "genre"
    name_field = "genre"
    related_search_vectors = [("genrealias___fts", SIMPLE)]

    class Meta(BaseModel.Meta):
        verbose_name = "Genre"
        verbose_name_plural = "Genres"
        ordering = ["genre"]

    @staticmethod
    def get_overview_annotations() -> dict:
        return {"alias_list": string_list("genrealias__alias")}


class GenreAlias(BaseAliasModel):
    parent = models.ForeignKey("Genre", models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("alias", "B", SIMPLE),
        ]
    )


class Band(BaseModel):
    band_name = models.CharField("Bandname", max_length=200)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. der Band")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    genre = models.ManyToManyField("Genre")
    musiker = models.ManyToManyField("Musiker")
    orte = models.ManyToManyField("Ort")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("band_name", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ],
    )

    create_field = "band_name"
    name_field = "band_name"
    related_search_vectors = [("bandalias___fts", SIMPLE)]

    class Meta(BaseModel.Meta):
        verbose_name = "Band"
        verbose_name_plural = "Bands"
        ordering = ["band_name"]

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "genre_list": string_list("genre__genre"),
            "musiker_list": string_list("musiker__kuenstler_name"),
            "alias_list": string_list("bandalias__alias"),
            "orte_list": string_list("orte___name", sep="; "),
        }


class BandAlias(BaseAliasModel):
    parent = models.ForeignKey("Band", models.CASCADE)

    _fts = SearchVectorField(
        columns=[WeightedColumn("alias", "B", SIMPLE)],
    )


class BandURL(AbstractURLModel):
    # TODO: field name is wrong
    brochure = models.ForeignKey("Band", models.CASCADE, related_name="urls")


class Autor(ComputedNameModel):
    kuerzel = models.CharField("Kürzel", max_length=8, blank=True)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Autors")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    person = models.ForeignKey("Person", models.CASCADE, null=True, blank=True)

    magazin = models.ManyToManyField("Magazin")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("_name", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_composing_fields = ["person___name", "kuerzel"]
    related_search_vectors = [("person___fts", SIMPLE)]
    select_related = ("person",)

    class Meta(ComputedNameModel.Meta):
        verbose_name = "Autor"
        verbose_name_plural = "Autoren"

    @classmethod
    def _get_name(cls, **data: tuple) -> str:
        """
        Construct a name from the data given.

        Args:
             **data: mapping of field_path: tuple of values provided by
              MIZQuerySet.values_dict

        Returns a name in the format of either:
            - '{person_name}' if no kuerzel is given
            - '{kuerzel}' if no person name is given
            - '{person_name} ({kuerzel})' if both are given
        """
        person_name = kuerzel = ""
        if "kuerzel" in data:
            kuerzel = data["kuerzel"][0]
        if "person___name" in data:
            person_name = data["person___name"][0]
            # The person_name should not be a default value:
            # noinspection PyUnresolvedReferences
            person_default = Person._name_default % {"verbose_name": Person._meta.verbose_name}
            if person_name in (person_default, "unbekannt"):
                # person_name is a default value:
                # ('unbekannt' used to be the default for person__nachname)
                person_name = ""

        if person_name:
            if kuerzel:
                return "{} ({})".format(person_name, kuerzel)
            else:
                return person_name
        else:
            # noinspection PyUnresolvedReferences
            opts = cls._meta
            return kuerzel or cls._name_default % {"verbose_name": opts.verbose_name}

    @staticmethod
    def get_overview_annotations() -> dict:
        return {"magazin_list": string_list("magazin__magazin_name")}


class AutorURL(AbstractURLModel):
    # TODO: field name is wrong
    brochure = models.ForeignKey("Autor", models.CASCADE, related_name="urls")


class Ausgabe(ComputedNameModel):
    class Status(models.TextChoices):
        UNBEARBEITET = ("unb", "unbearbeitet")
        INBEARBEITUNG = ("iB", "in Bearbeitung")
        ABGESCHLOSSEN = ("abg", "abgeschlossen")
        KEINEBEARBEITUNG = ("kB", "keine Bearbeitung vorgesehen")

    status = models.CharField("Bearbeitungsstatus", max_length=40, choices=Status.choices, default=Status.UNBEARBEITET)
    e_datum = models.DateField("Erscheinungsdatum", null=True, blank=True)
    jahrgang = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Jahrgang", validators=[MinValueValidator(1)]
    )
    sonderausgabe = models.BooleanField("Sonderausgabe", default=False)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. der Ausgabe")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    magazin = models.ForeignKey("Magazin", models.PROTECT)

    audio = models.ManyToManyField("Audio")
    video = models.ManyToManyField("Video")

    # Add a field that stores the computed name without any forward slashes
    # specifically for the full text search.
    # See: https://github.com/Actionb/MIZDB/issues/14
    _fts_name = models.CharField(max_length=200, editable=False, default="")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("_fts_name", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_composing_fields = [
        "beschreibung",
        "sonderausgabe",
        "e_datum",
        "jahrgang",
        "magazin__ausgaben_merkmal",
        "ausgabejahr__jahr",
        "ausgabenum__num",
        "ausgabelnum__lnum",
        "ausgabemonat__monat__abk",
    ]
    # TODO: magazin___fts as a related_search_vector?
    select_related = ("magazin",)

    objects = AusgabeQuerySet.as_manager()

    class Meta(ComputedNameModel.Meta):
        verbose_name = "Ausgabe"
        verbose_name_plural = "Ausgaben"
        ordering = ["magazin"]

    def save(self, update=True, *args, **kwargs):
        super().save()
        if update and self._name.replace("/", "+") != self._fts_name:
            self.qs().update(_fts_name=self._name.replace("/", "+"), _changed_flag=False)

    @classmethod
    def _get_name(cls, **data: tuple) -> str:
        """
        Construct a name from the data given.

        Args:
             **data: mapping of field_path: tuple of values provided by
              MIZQuerySet.values_dict
        """
        beschreibung = ""
        if "beschreibung" in data:
            beschreibung = concat_limit(data["beschreibung"][0].split(), width=30, sep=" ")
        if "sonderausgabe" in data and data["sonderausgabe"][0] and beschreibung:
            # Special issues may be a bit... 'special' in their numerical values.
            # Just use the 'beschreibung' for such an issue.
            return beschreibung

        jahre = jahrgang = ""
        if "jahrgang" in data:
            jahrgang = str(data["jahrgang"][0])
        if "ausgabejahr__jahr" in data:
            # Concatenate the years given.
            # Use four digits for the first year. For other years, only use
            # their last two digits.
            jahre = [  # type: ignore[assignment]
                jahr[2:] if i else jahr for i, jahr in enumerate(sorted(str(j) for j in data["ausgabejahr__jahr"]))
            ]
            jahre = concat_limit(jahre, sep="/")
        if not jahre:
            # Use 'jahrgang' as a fallback or resort to 'k.A.'.
            if jahrgang:
                jahre = "Jg. {}".format(jahrgang)
            else:
                jahre = "k.A."

        e_datum = nums = lnums = monate = ""
        if "e_datum" in data:
            e_datum = data["e_datum"][0]
        if "ausgabenum__num" in data:
            nums = concat_limit(
                (n.zfill(2) for n in sorted(str(n) for n in data["ausgabenum__num"])),
                sep="/",
            )
        if "ausgabelnum__lnum" in data:
            lnums = concat_limit(
                (n.zfill(2) for n in sorted(str(n) for n in data["ausgabelnum__lnum"])),
                sep="/",
            )
        if "ausgabemonat__monat__abk" in data:
            monat_ordering = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
            # Sort the month abbreviations according to the calendar.
            monate = sorted(  # type: ignore[assignment]
                data["ausgabemonat__monat__abk"],
                key=lambda abk: monat_ordering.index(abk) + 1 if abk in monat_ordering else 0,
            )
            monate = concat_limit(monate, sep="/")
        # 'ausgaben_merkmal' acts as an override to what attribute should make
        # up the name. If that attribute is in data, use that directly.
        merkmal = ""
        if "magazin__ausgaben_merkmal" in data:
            merkmal = data["magazin__ausgaben_merkmal"][0]
        if merkmal:
            if merkmal == Magazin.Merkmal.E_DATUM and e_datum:
                return str(e_datum)
            elif merkmal == Magazin.Merkmal.MONAT and monate:
                return "{}-{}".format(jahre, monate)
            elif merkmal == Magazin.Merkmal.LNUM and lnums:
                if jahre == "k.A.":
                    return lnums
                else:
                    return "{} ({})".format(lnums, jahre)
            elif nums:
                return "{}-{}".format(jahre, nums)

        if nums:
            return "{}-{}".format(jahre, nums)
        if lnums:
            if jahre == "k.A.":
                return lnums
            else:
                return "{} ({})".format(lnums, jahre)
        if e_datum:
            return str(e_datum)
        if monate:
            return "{}-{}".format(jahre, monate)
        if beschreibung:
            return beschreibung
        # noinspection PyUnresolvedReferences
        opts = cls._meta
        return cls._name_default % {"verbose_name": opts.verbose_name}

    @staticmethod
    def get_overview_annotations() -> dict:
        # Can't use ArrayAgg directly to get a list of distinct monat__abk
        # values as we are ordering by monat__ordinal: using distinct AND
        # ordering requires that the ordering expressions are present in the
        # argument list to ArrayAgg.
        # Use a subquery instead:
        subquery = (
            Ausgabe.objects.order_by()
            .filter(id=OuterRef("id"))
            .annotate(
                x=array_to_string(
                    to_array("ausgabemonat__monat__abk", ordering="ausgabemonat__monat__ordinal", distinct=False)
                )
            )
            .values("x")
        )
        return {
            "jahr_list": string_list("ausgabejahr__jahr"),
            "num_list": string_list("ausgabenum__num"),
            "lnum_list": string_list("ausgabelnum__lnum"),
            "monat_list": Subquery(subquery),
            "anz_artikel": Count("artikel", distinct=True),
        }


class AusgabeJahr(BaseModel):
    jahr = YearField("Jahr")

    ausgabe = models.ForeignKey("Ausgabe", models.CASCADE)

    name_field = "jahr"

    class Meta(BaseModel.Meta):
        verbose_name = "Jahr"
        verbose_name_plural = "Jahre"
        unique_together = ("jahr", "ausgabe")
        ordering = ["jahr"]


class AusgabeNum(BaseModel):
    num = models.PositiveSmallIntegerField("Nummer")

    ausgabe = models.ForeignKey("Ausgabe", models.CASCADE)

    name_field = "num"

    class Meta(BaseModel.Meta):
        verbose_name = "Nummer"
        verbose_name_plural = "Ausgabennummer"
        unique_together = ("num", "ausgabe")
        ordering = ["num"]


class AusgabeLnum(BaseModel):
    lnum = models.PositiveSmallIntegerField("Lfd. Nummer")

    ausgabe = models.ForeignKey("Ausgabe", models.CASCADE)

    name_field = "lnum"

    class Meta(BaseModel.Meta):
        verbose_name = "lfd. Nummer"
        verbose_name_plural = "Laufende Nummer"
        unique_together = ("lnum", "ausgabe")
        ordering = ["lnum"]


class AusgabeMonat(BaseModel):
    ausgabe = models.ForeignKey("Ausgabe", models.CASCADE)
    monat = models.ForeignKey("Monat", models.CASCADE)

    name_field = "monat__abk"

    class Meta(BaseModel.Meta):
        verbose_name = "Ausgabe-Monat"
        verbose_name_plural = "Ausgabe-Monate"
        unique_together = ("ausgabe", "monat")
        ordering = ["monat"]

    def __str__(self) -> str:
        # noinspection PyUnresolvedReferences
        return self.monat.abk


class Monat(BaseModel):
    monat = models.CharField("Monat", max_length=200)
    abk = models.CharField("Abk", max_length=200)
    ordinal = models.PositiveSmallIntegerField(editable=False)

    _fts = SearchVectorField(columns=[WeightedColumn("monat", "A", SIMPLE), WeightedColumn("abk", "A", SIMPLE)])

    name_field = "monat"

    class Meta(BaseModel.Meta):
        verbose_name = "Monat"
        verbose_name_plural = "Monate"
        ordering = ["ordinal"]

    def __str__(self) -> str:
        return str(self.monat)


class Magazin(BaseModel):
    class Merkmal(models.TextChoices):
        NUM = ("num", "Nummer")
        LNUM = ("lnum", "Lfd.Nummer")
        MONAT = ("monat", "Monat")
        E_DATUM = ("e_datum", "Ersch.Datum")

    magazin_name = models.CharField("Magazin", max_length=200)
    ausgaben_merkmal = models.CharField(
        "Ausgaben Merkmal",
        max_length=8,
        blank=True,
        choices=Merkmal.choices,
        help_text=(
            "Das dominante Merkmal der Ausgaben. Diese Angabe bestimmt die "
            "Darstellung der Ausgaben in der Änderungsliste."
        ),
    )
    fanzine = models.BooleanField("Fanzine", default=False)
    issn = ISSNField(  # TODO: rename to 'ISBN' (Buch also uses all capitalized ISBN/EAN)
        "ISSN", blank=True, help_text="EAN (Barcode Nummer) Angaben erlaubt. Die ISSN wird dann daraus ermittelt."
    )
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Magazines")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    genre = models.ManyToManyField("Genre")
    verlag = models.ManyToManyField("Verlag")
    herausgeber = models.ManyToManyField("Herausgeber")
    orte = models.ManyToManyField("Ort")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("magazin_name", "A", SIMPLE),
            WeightedColumn("issn", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    create_field = "magazin_name"
    name_field = "magazin_name"

    class Meta(BaseModel.Meta):
        verbose_name = "Magazin"
        verbose_name_plural = "Magazine"
        ordering = ["magazin_name"]

    def __str__(self) -> str:
        return str(self.magazin_name)

    @staticmethod
    def get_overview_annotations() -> dict:
        return {"orte_list": string_list("orte___name", sep="; "), "anz_ausgaben": Count("ausgabe", distinct=True)}


class MagazinURL(AbstractURLModel):
    magazin = models.ForeignKey("Magazin", models.CASCADE, related_name="urls")


class Verlag(BaseModel):
    verlag_name = models.CharField("Verlag", max_length=200)

    sitz = models.ForeignKey("Ort", models.SET_NULL, null=True, blank=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("verlag_name", "A", SIMPLE),
        ]
    )

    create_field = "verlag_name"
    name_field = "verlag_name"
    select_related = ("sitz",)

    class Meta(BaseModel.Meta):
        verbose_name = "Verlag"
        verbose_name_plural = "Verlage"
        ordering = ["verlag_name", "sitz"]


class Ort(ComputedNameModel):
    stadt = models.CharField(max_length=200, blank=True)

    bland = models.ForeignKey("bundesland", models.SET_NULL, verbose_name="Bundesland", null=True, blank=True)
    land = models.ForeignKey("Land", models.PROTECT)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("_name", "A", SIMPLE),
        ]
    )

    name_composing_fields = ["stadt", "land__land_name", "bland__bland_name", "land__code", "bland__code"]
    select_related = ("land", "bland")

    class Meta(ComputedNameModel.Meta):
        verbose_name = "Ort"
        verbose_name_plural = "Orte"
        unique_together = ("stadt", "bland", "land")
        ordering = ["land", "bland", "stadt"]

    @classmethod
    def _get_name(cls, **data: tuple) -> str:
        """
        Construct a name from the data given.

        Args:
             **data: mapping of field_path: tuple of values provided by
              MIZQuerySet.values_dict

        Returns a name in the format of either:
            - '{stadt}, {a combination of bundesland_code and land_code}'
            - '{stadt}, {land_code}'
            - '{bundesland}, {land_code}'
            - '{land_name}'
        """
        stadt = bundesland = bundesland_code = land = land_code = ""
        if "stadt" in data:
            stadt = data["stadt"][0]
        if "bland__bland_name" in data:
            bundesland = data["bland__bland_name"][0]
        if "bland__code" in data:
            bundesland_code = data["bland__code"][0]
        if "land__land_name" in data:
            land = data["land__land_name"][0]
        if "land__code" in data:
            land_code = data["land__code"][0]

        result_template = "{}, {}"
        if stadt:
            if bundesland_code:
                codes = land_code + "-" + bundesland_code
                return result_template.format(stadt, codes)
            else:
                return result_template.format(stadt, land_code)
        else:
            if bundesland:
                return result_template.format(bundesland, land_code)
            else:
                return land


class Bundesland(BaseModel):
    bland_name = models.CharField("Bundesland", max_length=200)
    code = models.CharField(max_length=4, unique=False)

    land = models.ForeignKey("Land", models.PROTECT)

    _fts = SearchVectorField(columns=[WeightedColumn("bland_name", "A", SIMPLE), WeightedColumn("code", "A", SIMPLE)])

    name_field = "bland_name"

    def __str__(self) -> str:
        return "{} {}".format(self.bland_name, self.code).strip()

    class Meta(BaseModel.Meta):
        verbose_name = "Bundesland"
        verbose_name_plural = "Bundesländer"
        unique_together = ("bland_name", "land")
        ordering = ["land", "bland_name"]


class Land(BaseModel):
    land_name = models.CharField("Land", max_length=100, unique=True)
    code = models.CharField(max_length=4, unique=True)

    _fts = SearchVectorField(columns=[WeightedColumn("land_name", "A", SIMPLE), WeightedColumn("code", "A", SIMPLE)])

    name_field = "land_name"

    def __str__(self) -> str:
        return "{} {}".format(self.land_name, self.code).strip()

    class Meta(BaseModel.Meta):
        verbose_name = "Land"
        verbose_name_plural = "Länder"
        ordering = ["land_name"]


# TODO: make schlagwort 'view-only' in admin (meta.default_permissions)
class Schlagwort(BaseModel):
    schlagwort = models.CharField(max_length=100, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("schlagwort", "A", SIMPLE),
        ]
    )

    create_field = "schlagwort"
    name_field = "schlagwort"
    related_search_vectors = [("schlagwortalias___fts", SIMPLE)]

    class Meta(BaseModel.Meta):
        verbose_name = "Schlagwort"
        verbose_name_plural = "Schlagwörter"
        ordering = ["schlagwort"]

    @staticmethod
    def get_overview_annotations() -> dict:
        return {"alias_list": string_list("schlagwortalias__alias")}


class SchlagwortAlias(BaseAliasModel):
    parent = models.ForeignKey("Schlagwort", models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("alias", "A", SIMPLE),
        ]
    )


class Artikel(BaseModel):
    class Umfang(models.TextChoices):
        F = ("f", "f")
        FF = ("ff", "ff")

    schlagzeile = models.CharField(max_length=200)  # TODO: use TextField?
    seite = models.PositiveSmallIntegerField()
    seitenumfang = models.CharField(
        max_length=3,
        blank=True,
        choices=Umfang.choices,
        default="",
        help_text="Zwei Seiten: f; mehr als zwei Seiten: ff.",
    )
    zusammenfassung = models.TextField(blank=True)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Artikels")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    ausgabe = models.ForeignKey("Ausgabe", models.PROTECT)

    autor = models.ManyToManyField("Autor")
    musiker = models.ManyToManyField("Musiker")
    band = models.ManyToManyField("Band")
    schlagwort = models.ManyToManyField("Schlagwort")
    genre = models.ManyToManyField("Genre")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")
    person = models.ManyToManyField("Person")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("schlagzeile", "A", SIMPLE),
            WeightedColumn("zusammenfassung", "B", STEMMING),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "schlagzeile"
    select_related = ("ausgabe", "ausgabe__magazin")

    class Meta(BaseModel.Meta):
        verbose_name = "Artikel"
        verbose_name_plural = "Artikel"
        ordering = [
            # TODO: ordering by ausgabe___name doesn't work well when name
            #   contains months (1970-Dez comes before 1970-Nov).
            #   (might be a PRO for introducing an order column on Ausgabe?)
            "ausgabe__magazin__magazin_name",
            "ausgabe___name",
            "seite",
            "schlagzeile",
        ]

    def __str__(self) -> str:
        if self.schlagzeile:
            return str(self.schlagzeile)
        elif self.zusammenfassung:
            return str(self.zusammenfassung)
        else:
            return "Keine Schlagzeile gegeben!"

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "kuenstler_list": limit(array_to_string(to_array("band__band_name"), to_array("musiker__kuenstler_name"))),
        }


class Buch(BaseModel):
    # TODO: übersetzer feld
    # TODO: use TextField instead of CharField for titel, titel_orig
    titel = models.CharField(max_length=200)
    titel_orig = models.CharField("Titel (Original)", max_length=200, blank=True)
    seitenumfang = models.PositiveSmallIntegerField(blank=True, null=True)
    jahr = YearField("Jahr", null=True, blank=True)
    jahr_orig = YearField("Jahr (Original)", null=True, blank=True)
    auflage = models.CharField(max_length=200, blank=True)
    EAN = EANField(blank=True)
    ISBN = ISBNField(blank=True)
    is_buchband = models.BooleanField(
        default=False,
        verbose_name="Ist Sammelband",
        help_text="Dieses Buch ist ein Sammelband bestehend aus Aufsätzen.",
    )
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Buches")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    schriftenreihe = models.ForeignKey("Schriftenreihe", models.SET_NULL, null=True, blank=True)
    buchband = models.ForeignKey(
        "self",
        models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={"is_buchband": True},
        related_name="buch_set",
        help_text="Der Sammelband, der diesen Aufsatz enthält.",
        verbose_name="Sammelband",
    )
    sprache = models.CharField(max_length=200, blank=True)

    autor = models.ManyToManyField("Autor")
    musiker = models.ManyToManyField("Musiker")
    band = models.ManyToManyField("Band")
    schlagwort = models.ManyToManyField("Schlagwort")
    genre = models.ManyToManyField("Genre")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")
    person = models.ManyToManyField("Person")
    herausgeber = models.ManyToManyField("Herausgeber")
    verlag = models.ManyToManyField("Verlag")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"

    class Meta(BaseModel.Meta):
        ordering = ["titel"]
        verbose_name = "Buch"
        verbose_name_plural = "Bücher"

    def __str__(self) -> str:
        return str(self.titel)

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "autor_list": string_list("autor___name"),
            "schlagwort_list": string_list("schlagwort__schlagwort"),
            "kuenstler_list": limit(array_to_string(to_array("band__band_name"), to_array("musiker__kuenstler_name"))),
        }


class Herausgeber(BaseModel):
    herausgeber = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("herausgeber", "A", SIMPLE),
        ]
    )

    name_field = "herausgeber"
    create_field = "herausgeber"

    class Meta(BaseModel.Meta):
        ordering = ["herausgeber"]
        verbose_name = "Herausgeber"
        verbose_name_plural = "Herausgeber"


class Instrument(BaseModel):
    instrument = models.CharField(unique=True, max_length=200)
    kuerzel = models.CharField("Kürzel", max_length=8, blank=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("instrument", "A", SIMPLE),
            WeightedColumn("kuerzel", "A", SIMPLE),
        ]
    )

    name_field = "instrument"

    class Meta(BaseModel.Meta):
        ordering = ["instrument", "kuerzel"]
        verbose_name = "Instrument"
        verbose_name_plural = "Instrumente"

    def __str__(self) -> str:
        if self.kuerzel:
            return "{} ({})".format(str(self.instrument), str(self.kuerzel))
        return str(self.instrument)


class Audio(BaseModel):
    titel = models.CharField(max_length=200)
    tracks = models.PositiveIntegerField("Anz. Tracks", blank=True, null=True)
    laufzeit = models.DurationField(
        blank=True, null=True, help_text="Format: hh:mm:ss. Beispiel Laufzeit von 144 Minuten: 0:144:0."
    )
    jahr = YearField("Jahr", blank=True, null=True)
    land_pressung = models.ForeignKey("Land", models.PROTECT, blank=True, null=True, verbose_name="Land der Pressung")
    quelle = models.CharField(
        max_length=200, blank=True, help_text="Angaben zur Herkunft/Qualität der Aufnahme: z.B. Broadcast, Live, etc."
    )
    original = models.BooleanField(
        "Originalmaterial", default=False, help_text="Ist das vorliegende Material ein Original?"
    )
    plattennummer = models.CharField(max_length=200, blank=True)
    release_id = models.PositiveIntegerField("Release ID (discogs)", blank=True, null=True)
    discogs_url = models.URLField(
        "Link discogs.com", blank=True, help_text="Adresse zur discogs.com Seite dieses Objektes."
    )
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Audio Materials")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    medium = models.ForeignKey(
        "AudioMedium",
        models.PROTECT,
        blank=True,
        null=True,
        verbose_name="Speichermedium",
        help_text="Format des Speichermediums.",
    )
    medium_qty = models.PositiveSmallIntegerField(
        "Anzahl", blank=True, null=True, default=1, validators=[MinValueValidator(1)]
    )

    musiker = models.ManyToManyField("Musiker", through=_m2m.m2m_audio_musiker)
    band = models.ManyToManyField("Band")
    schlagwort = models.ManyToManyField("Schlagwort")
    genre = models.ManyToManyField("Genre")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")
    person = models.ManyToManyField("Person")
    plattenfirma = models.ManyToManyField("Plattenfirma")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"
    select_related = ("medium",)

    objects = AudioQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        ordering = ["titel"]
        verbose_name = "Audio Material"
        verbose_name_plural = "Audio Materialien"

    def __str__(self) -> str:
        return str(self.titel)

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "kuenstler_list": limit(array_to_string(to_array("band__band_name"), to_array("musiker__kuenstler_name")))
        }


class AudioMedium(BaseModel):
    medium = models.CharField(max_length=200, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("medium", "A", SIMPLE),
        ]
    )

    create_field = "medium"
    name_field = "medium"

    class Meta(BaseModel.Meta):
        verbose_name = "Audio-Medium"
        verbose_name_plural = "Audio-Medium"
        ordering = ["medium"]


class Plakat(BaseModel):
    titel = models.CharField(max_length=200)
    # TODO: delete model field 'signatur' (it's no longer in use)
    signatur = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        unique=True,
        help_text=(
            "Kürzel bestehend aus Angabe zur Größe und einer 5-stelligen fortlaufenden Nummer. Z.B.: DINA2-00395"
        ),
    )
    size = models.CharField("Größe", max_length=200, blank=True)
    datum = PartialDateField("Zeitangabe")
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Plakates")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    reihe = models.ForeignKey("Bildreihe", models.PROTECT, blank=True, null=True, verbose_name="Bildreihe")

    schlagwort = models.ManyToManyField("Schlagwort")
    genre = models.ManyToManyField("Genre")
    musiker = models.ManyToManyField("Musiker")
    band = models.ManyToManyField("Band")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")
    person = models.ManyToManyField("Person")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("signatur", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"

    class Meta(BaseModel.Meta):
        ordering = ["titel"]
        verbose_name = "Plakat"
        verbose_name_plural = "Plakate"

    @staticmethod
    def get_overview_annotations() -> dict:
        return {"veranstaltung_list": string_list("veranstaltung__name")}


class Bildreihe(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("name", "A", SIMPLE),
        ]
    )

    create_field = "name"
    name_field = "name"

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = "Bildreihe"
        verbose_name_plural = "Bildreihen"


class Schriftenreihe(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("name", "A", SIMPLE),
        ]
    )

    create_field = "name"
    name_field = "name"

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = "Schriftenreihe"
        verbose_name_plural = "Schriftenreihen"


class Dokument(BaseModel):
    titel = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Dokumentes")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    genre = models.ManyToManyField("Genre")
    schlagwort = models.ManyToManyField("Schlagwort")
    person = models.ManyToManyField("Person")
    band = models.ManyToManyField("Band")
    musiker = models.ManyToManyField("Musiker")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"

    class Meta(BaseModel.Meta):
        ordering = ["titel"]
        verbose_name = "Dokument"
        verbose_name_plural = "Dokumente"


class Memorabilien(BaseModel):
    titel = models.CharField(max_length=200)
    typ = models.ForeignKey(
        "MemoTyp", on_delete=models.PROTECT, blank=True, null=True, verbose_name="Art d. Memorabilie"
    )
    beschreibung = models.TextField(blank=True, help_text="Beschreibung der Memorabilie")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    genre = models.ManyToManyField("Genre")
    schlagwort = models.ManyToManyField("Schlagwort")
    person = models.ManyToManyField("Person")
    band = models.ManyToManyField("Band")
    musiker = models.ManyToManyField("Musiker")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"

    class Meta(BaseModel.Meta):
        verbose_name = "Memorabilie"
        verbose_name_plural = "Memorabilien"
        ordering = ["titel"]

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "kuenstler_list": limit(array_to_string(to_array("band__band_name"), to_array("musiker__kuenstler_name"))),
        }


class MemoTyp(BaseModel):
    name = models.CharField("Typ", max_length=100, unique=True)

    _fts = SearchVectorField(columns=[WeightedColumn("name", "A", SIMPLE)])

    create_field = "name"
    name_field = "name"

    class Meta(BaseModel.Meta):
        verbose_name = "Memorabilie-Typ"
        verbose_name_plural = "Memorabilie-Typen"
        ordering = ["name"]


class Spielort(BaseModel):
    name = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Spielortes")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    ort = models.ForeignKey("Ort", models.PROTECT)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("name", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "name"
    related_search_vectors = [("spielortalias___fts", SIMPLE), ("ort___fts", SIMPLE)]
    select_related = ("ort",)

    class Meta(BaseModel.Meta):
        verbose_name = "Spielort"
        verbose_name_plural = "Spielorte"
        ordering = ["name", "ort"]


class SpielortURL(AbstractURLModel):
    # TODO: field name is wrong
    brochure = models.ForeignKey("Spielort", models.CASCADE, related_name="urls")


class SpielortAlias(BaseAliasModel):
    parent = models.ForeignKey("Spielort", models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("alias", "A", SIMPLE),
        ]
    )


class Technik(BaseModel):
    titel = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. der Technik")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    genre = models.ManyToManyField("Genre")
    schlagwort = models.ManyToManyField("Schlagwort")
    person = models.ManyToManyField("Person")
    band = models.ManyToManyField("Band")
    musiker = models.ManyToManyField("Musiker")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"

    class Meta(BaseModel.Meta):
        verbose_name = "Technik"
        verbose_name_plural = "Technik"
        ordering = ["titel"]


class Veranstaltung(BaseModel):
    name = models.CharField(max_length=200)  # TODO: use TextField
    datum = PartialDateField(blank=False)

    spielort = models.ForeignKey("Spielort", models.PROTECT)
    reihe = models.ForeignKey("Veranstaltungsreihe", models.PROTECT, blank=True, null=True)

    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. der Veranstaltung")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    musiker = models.ManyToManyField("Musiker")
    band = models.ManyToManyField("Band")
    schlagwort = models.ManyToManyField("Schlagwort")
    genre = models.ManyToManyField("Genre")
    person = models.ManyToManyField("Person")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("name", "A", SIMPLE),
            WeightedColumn("datum", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "name"
    related_search_vectors = [
        ("veranstaltungalias___fts", SIMPLE),
        ("spielort___fts", SIMPLE),
        ("spielort__ort___fts", SIMPLE),
    ]
    select_related = ("spielort", "reihe")

    class Meta(BaseModel.Meta):
        verbose_name = "Veranstaltung"
        verbose_name_plural = "Veranstaltungen"
        ordering = ["name", "datum", "spielort"]

    require_confirmation = True  # FIXME: what is this doing here?

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "kuenstler_list": limit(array_to_string(to_array("band__band_name"), to_array("musiker__kuenstler_name")))
        }


class VeranstaltungAlias(BaseAliasModel):
    parent = models.ForeignKey("Veranstaltung", models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("alias", "A", SIMPLE),
        ]
    )


class VeranstaltungURL(AbstractURLModel):
    # TODO: field name is wrong
    brochure = models.ForeignKey("Veranstaltung", models.CASCADE, related_name="urls")


class Veranstaltungsreihe(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("name", "A", SIMPLE),
        ]
    )

    create_field = "name"
    name_field = "name"

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = "Veranstaltungsreihe"
        verbose_name_plural = "Veranstaltungsreihen"


class Video(BaseModel):
    titel = models.CharField(max_length=200)  # TODO: use TextField
    laufzeit = models.DurationField(
        blank=True, null=True, help_text="Format: hh:mm:ss. Beispiel Laufzeit von 144 Minuten: 0:144:0."
    )
    jahr = YearField("Jahr", blank=True, null=True)
    quelle = models.CharField(
        max_length=200, blank=True, help_text="Angaben zur Herkunft/Qualität der Aufnahme: z.B. Broadcast, Live, etc."
    )
    original = models.BooleanField(
        "Originalmaterial", default=False, help_text="Ist das vorliegende Material ein Original?"
    )
    release_id = models.PositiveIntegerField("Release ID (discogs)", blank=True, null=True)
    discogs_url = models.URLField(
        "Link discogs.com", blank=True, help_text="Adresse zur discogs.com Seite dieses Objektes."
    )
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Video Materials")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    medium = models.ForeignKey(
        "VideoMedium",
        models.PROTECT,
        blank=True,
        null=True,
        verbose_name="Speichermedium",
        help_text="Format des Speichermediums.",
    )
    medium_qty = models.PositiveSmallIntegerField(
        "Anzahl", blank=True, null=True, default=1, validators=[MinValueValidator(1)]
    )

    musiker = models.ManyToManyField("Musiker", through=_m2m.m2m_video_musiker)
    band = models.ManyToManyField("Band")
    schlagwort = models.ManyToManyField("Schlagwort")
    genre = models.ManyToManyField("Genre")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")
    person = models.ManyToManyField("Person")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"
    select_related = ("medium",)

    class Meta(BaseModel.Meta):
        verbose_name = "Video Material"
        verbose_name_plural = "Video Materialien"
        ordering = ["titel"]

    @staticmethod
    def get_overview_annotations() -> dict:
        return {
            "kuenstler_list": limit(array_to_string(to_array("band__band_name"), to_array("musiker__kuenstler_name")))
        }


class VideoMedium(BaseModel):
    medium = models.CharField(max_length=200, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("medium", "A", SIMPLE),
        ]
    )

    create_field = "medium"
    name_field = "medium"

    class Meta(BaseModel.Meta):
        verbose_name = "Video-Medium"
        verbose_name_plural = "Video-Medium"
        ordering = ["medium"]


class Provenienz(BaseModel):
    class Types(models.TextChoices):
        SCHENKUNG = "Schenkung"
        SPENDE = "Spende"
        FUND = "Fund"
        LEIHGABE = "Leihgabe"
        DAUERLEIHGABE = "Dauerleihgabe"

    typ = models.CharField("Art der Provenienz", max_length=100, choices=Types.choices, default=Types.SCHENKUNG)

    geber = models.ForeignKey("Geber", models.PROTECT)

    name_field = "geber__name"
    related_search_vectors = [("geber___fts", SIMPLE)]
    select_related = ("geber",)

    class Meta(BaseModel.Meta):
        ordering = ["geber", "typ"]
        verbose_name = "Provenienz"
        verbose_name_plural = "Provenienzen"

    def __str__(self) -> str:
        return "{0} ({1})".format(str(self.geber.name), str(self.typ))


class Geber(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(columns=[WeightedColumn("name", "A", SIMPLE)])

    name_field = create_field = "name"

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = "Geber"
        verbose_name_plural = "Geber"


class Lagerort(ComputedNameModel):
    ort = models.CharField(max_length=200)
    raum = models.CharField(max_length=200, blank=True)
    regal = models.CharField(max_length=200, blank=True)
    fach = models.CharField(max_length=200, blank=True)
    ordner = models.CharField(max_length=200, blank=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("_name", "A", SIMPLE),
        ]
    )

    name_composing_fields = ["ort", "raum", "regal", "fach"]

    class Meta(BaseModel.Meta):
        verbose_name = "Lagerort"
        verbose_name_plural = "Lagerorte"
        ordering = ["_name"]

    @classmethod
    def _get_name(cls, **data: tuple) -> str:
        """
        Construct a name from the data given.

        Args:
             **data: mapping of field_path: tuple of values provided by
              MIZQuerySet.values_dict

        Returns a name in the format of either:
            - '{a combination of fach/regal/raum} ({ort})'
            - '{ort}'
        """
        ort = raum = regal = fach = ""
        if "ort" in data:
            ort = data["ort"][0]
        if "raum" in data:
            raum = data["raum"][0]
        if "regal" in data:
            regal = data["regal"][0]
        if "fach" in data:
            fach = data["fach"][0]

        if regal and fach:
            regal = "{}-{}".format(regal, fach)
        if raum:
            if regal:
                regal = "{}-{}".format(raum, regal)
            else:
                return "{} ({})".format(raum, ort)
        if regal:
            return "{} ({})".format(regal, ort)
        else:
            return ort


class Bestand(BaseModel):
    signatur = models.AutoField(primary_key=True)
    lagerort = models.ForeignKey("Lagerort", models.PROTECT)
    anmerkungen = models.TextField(blank=True)
    provenienz = models.ForeignKey("Provenienz", models.SET_NULL, blank=True, null=True)

    audio = models.ForeignKey("Audio", models.CASCADE, blank=True, null=True)
    ausgabe = models.ForeignKey("Ausgabe", models.CASCADE, blank=True, null=True)
    brochure = models.ForeignKey("BaseBrochure", models.CASCADE, blank=True, null=True)
    buch = models.ForeignKey("Buch", models.CASCADE, blank=True, null=True)
    dokument = models.ForeignKey("Dokument", models.CASCADE, blank=True, null=True)
    foto = models.ForeignKey("Foto", models.CASCADE, blank=True, null=True)
    memorabilien = models.ForeignKey("Memorabilien", models.CASCADE, blank=True, null=True)
    plakat = models.ForeignKey("Plakat", models.CASCADE, blank=True, null=True)
    technik = models.ForeignKey("Technik", models.CASCADE, blank=True, null=True)
    video = models.ForeignKey("Video", models.CASCADE, blank=True, null=True)

    _fts = SearchVectorField(columns=[WeightedColumn("anmerkungen", "A", STEMMING)])

    select_related = ("lagerort", "provenienz__geber")

    name_field = "lagerort___name"

    class Meta(BaseModel.Meta):
        verbose_name = "Bestand"
        verbose_name_plural = "Bestände"
        ordering = ["pk"]

    def __str__(self) -> str:
        return str(self.lagerort)

    @property
    def bestand_object(self) -> Optional[models.Model]:
        """Return the archive object this Bestand instance refers to."""
        if hasattr(self, "_bestand_object"):  # pragma: no cover
            return self._bestand_object
        self._bestand_object: Optional[models.Model] = None
        for field in get_model_fields(self, base=False, foreign=True, m2m=False):
            # The archive object is referenced by the one FK relation (other
            # than Lagerort and Provenienz) that is not null.
            if field.related_model._meta.object_name in ("Lagerort", "Provenienz"):
                continue
            related_obj = getattr(self, field.name)
            if related_obj:
                if related_obj._meta.object_name == "BaseBrochure":
                    # Handle the multiple inheritance stuff:
                    related_obj = related_obj.resolve_child()
                self._bestand_object = related_obj
        return self._bestand_object


class Datei(BaseModel):
    class Media(models.TextChoices):
        # TODO: consider using values in all capitals and in alphabetical order
        #  (this would require a migration)
        AUDIO = "audio"
        VIDEO = "video"
        BILD = "bild"
        TEXT = "text"
        SONSTIGE = "sonstige"

    titel = models.CharField(max_length=200)  # TODO: use TextField
    media_typ = models.CharField("Media Typ", max_length=200, choices=Media.choices, default=Media.AUDIO)
    datei_media = models.FileField(  # Datei Media Server
        "Datei", blank=True, null=True, editable=False, help_text="Datei auf Datenbank-Server hoch- bzw herunterladen."
    )
    datei_pfad = models.CharField(  # TODO: use TextField
        "Datei-Pfad",
        max_length=200,
        blank=True,
        help_text="Pfad (inklusive Datei-Namen und Endung) zur Datei im gemeinsamen Ordner.",
    )
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. der Datei")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    provenienz = models.ForeignKey("Provenienz", models.SET_NULL, blank=True, null=True)

    genre = models.ManyToManyField("Genre")
    schlagwort = models.ManyToManyField("Schlagwort")
    person = models.ManyToManyField("Person")
    band = models.ManyToManyField("Band")
    musiker = models.ManyToManyField("Musiker", through=_m2m.m2m_datei_musiker)
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"

    class Meta(BaseModel.Meta):
        ordering = ["titel"]
        verbose_name = "Datei"
        verbose_name_plural = "Dateien"

    def __str__(self) -> str:
        return str(self.titel)


class Plattenfirma(BaseModel):
    name = models.CharField(max_length=200)  # TODO: use TextField

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("name", "A", SIMPLE),
        ]
    )

    name_field = create_field = "name"

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = "Plattenfirma"
        verbose_name_plural = "Plattenfirmen"


class BrochureYear(AbstractJahrModel):
    brochure = models.ForeignKey("BaseBrochure", models.CASCADE, related_name="jahre")


class BrochureURL(AbstractURLModel):
    brochure = models.ForeignKey("BaseBrochure", models.CASCADE, related_name="urls")


class BaseBrochure(BaseModel):
    titel = models.CharField(max_length=200)  # TODO: use TextField
    zusammenfassung = models.TextField(blank=True)
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    ausgabe = models.ForeignKey(
        "ausgabe", models.SET_NULL, related_name="beilagen", verbose_name="Ausgabe", blank=True, null=True
    )

    genre = models.ManyToManyField("Genre")

    _base_fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("zusammenfassung", "B", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"

    def __str__(self) -> str:
        return str(self.titel)

    def resolve_child(self) -> models.Model:
        """Fetch a child instance from this parent instance."""
        # NOTE: technically a BaseBrochure can have more than one child (one
        #  from each model that inherits it) - and this returns the first child
        #  found.
        for rel in get_model_relations(self, forward=False, reverse=True):
            # Look for a reverse relation that is a PK and originates from a
            # subclass.
            if not rel.field.primary_key:
                continue
            if not issubclass(rel.related_model, self.__class__):
                continue
            try:
                return getattr(self, rel.name)
            except getattr(self.__class__, rel.name).RelatedObjectDoesNotExist:
                # This subclass is not related to this BaseBrochure instance.
                continue

    @staticmethod
    def get_overview_annotations() -> dict:
        return {"jahr_list": string_list("jahre__jahr")}

    class Meta(BaseModel.Meta):
        ordering = ["titel"]


class Brochure(BaseBrochure):
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. der Broschüre")

    schlagwort = models.ManyToManyField("Schlagwort")
    # TODO: add spielort ManyToManyField or merge all the BaseBrochure models?
    # (assuming a Brochure is specifically about a venue/s)

    _fts = SearchVectorField(columns=[WeightedColumn("beschreibung", "C", STEMMING)])

    related_search_vectors = [
        ("basebrochure_ptr___base_fts", SIMPLE),
        ("basebrochure_ptr___base_fts", STEMMING),
    ]

    class Meta(BaseBrochure.Meta):
        verbose_name = "Broschüre"
        verbose_name_plural = "Broschüren"


class Kalender(BaseBrochure):
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Programmheftes")

    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")

    _fts = SearchVectorField(columns=[WeightedColumn("beschreibung", "C", STEMMING)])

    related_search_vectors = [
        ("basebrochure_ptr___base_fts", SIMPLE),
        ("basebrochure_ptr___base_fts", STEMMING),
    ]

    class Meta(BaseBrochure.Meta):
        verbose_name = "Programmheft"
        verbose_name_plural = "Programmhefte"


class Katalog(BaseBrochure):
    class Types(models.TextChoices):
        MERCH = ("merch", "Merchandise")
        TECH = ("tech", "Instrumente & Technik")
        TON = ("ton", "Tonträger")
        BUCH = ("buch", "Bücher")
        OTHER = ("other", "Anderes")

    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Kataloges")
    art = models.CharField("Art d. Kataloges", max_length=40, choices=Types.choices, default=Types.MERCH)

    _fts = SearchVectorField(columns=[WeightedColumn("beschreibung", "C", STEMMING)])

    related_search_vectors = [
        ("basebrochure_ptr___base_fts", SIMPLE),
        ("basebrochure_ptr___base_fts", STEMMING),
    ]

    class Meta(BaseBrochure.Meta):
        verbose_name = "Warenkatalog"
        verbose_name_plural = "Warenkataloge"


class Foto(BaseModel):
    class Types(models.TextChoices):
        NEGATIV = ("negativ", "negativ")
        POSITIV = ("positiv", "positiv")
        REPRINT = ("reprint", "Neuabzug (reprint)")
        POLAROID = ("polaroid", "Polaroid")

    titel = models.CharField(max_length=200)  # TODO: use TextField
    size = models.CharField("Größe", max_length=200, blank=True)
    datum = PartialDateField("Zeitangabe")
    typ = models.CharField("Art des Fotos", max_length=100, choices=Types.choices, default=Types.NEGATIV)
    farbe = models.BooleanField("Farbfoto")
    owner = models.CharField("Rechteinhaber", max_length=200, blank=True)
    beschreibung = models.TextField(blank=True, help_text="Beschreibung bzgl. des Fotos")
    bemerkungen = models.TextField(blank=True, help_text="Kommentare für Archiv-Mitarbeiter")

    reihe = models.ForeignKey("Bildreihe", models.PROTECT, blank=True, null=True, verbose_name="Bildreihe")

    schlagwort = models.ManyToManyField("Schlagwort")
    genre = models.ManyToManyField("Genre")
    musiker = models.ManyToManyField("Musiker")
    band = models.ManyToManyField("Band")
    ort = models.ManyToManyField("Ort")
    spielort = models.ManyToManyField("Spielort")
    veranstaltung = models.ManyToManyField("Veranstaltung")
    person = models.ManyToManyField("Person")

    _fts = SearchVectorField(
        columns=[
            WeightedColumn("titel", "A", SIMPLE),
            WeightedColumn("beschreibung", "C", STEMMING),
            WeightedColumn("bemerkungen", "D", SIMPLE),
        ]
    )

    name_field = "titel"

    class Meta(BaseModel.Meta):
        ordering = ["titel"]
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"

    @staticmethod
    def get_overview_annotations() -> dict:
        return {"schlagwort_list": string_list("schlagwort__schlagwort")}
