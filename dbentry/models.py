# TODO: Semantik buch.buchband: Einzelbänder/Aufsätze: Teile eines Buchbandes
from typing import Optional

from django.core.validators import MinValueValidator
from django.db import models


import dbentry.m2m as _m2m
from dbentry.base.models import (
    AbstractJahrModel, AbstractURLModel, BaseAliasModel, BaseModel, ComputedNameModel
)
from dbentry.constants import LIST_DISPLAY_MAX_LEN
from dbentry.fields import (
    EANField, ISBNField, ISSNField, PartialDate, PartialDateField, YearField
)
from dbentry.fts.fields import SearchVectorField, WeightedColumn
from dbentry.managers import AusgabeQuerySet, HumanNameQuerySet, PeopleQuerySet
from dbentry.utils import concat_limit, get_model_fields, get_model_relations


class Person(ComputedNameModel):
    vorname = models.CharField(max_length=200, blank=True)
    nachname = models.CharField(max_length=200)

    gnd_id = models.CharField('Normdatei ID', max_length=20, blank=True)
    gnd_name = models.CharField('Normdatei Name', max_length=200, blank=True)
    dnb_url = models.URLField(
        'Link DNB', blank=True,
        help_text="Adresse zur Seite dieser Person in der Deutschen Nationalbibliothek."
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Person')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    orte = models.ManyToManyField('Ort')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('_name', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_composing_fields = ['vorname', 'nachname']
    primary_search_fields = ['_name']
    search_fields = ['_name', 'beschreibung', 'bemerkungen']

    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Person'
        verbose_name_plural = 'Personen'

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
        vorname = nachname = ''
        if 'vorname' in data:
            vorname = data['vorname'][0]
        if 'nachname' in data:
            nachname = data['nachname'][0]
        if vorname or nachname:
            return "{} {}".format(vorname, nachname).strip()
        # noinspection PyUnresolvedReferences
        opts = cls._meta
        return cls._name_default % {'verbose_name': opts.verbose_name}


class PersonURL(AbstractURLModel):
    brochure = models.ForeignKey('Person', models.CASCADE, related_name='urls')


class Musiker(BaseModel):
    kuenstler_name = models.CharField('Künstlername', max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Musikers')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    person = models.ForeignKey('Person', models.SET_NULL, null=True, blank=True)

    genre = models.ManyToManyField('Genre')
    instrument = models.ManyToManyField('Instrument')
    orte = models.ManyToManyField('Ort')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('kuenstler_name', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    create_field = 'kuenstler_name'
    name_field = 'kuenstler_name'
    primary_search_fields = ['kuenstler_name']
    search_fields = [
        'kuenstler_name', 'musikeralias__alias', 'person___name',
        'beschreibung', 'bemerkungen'
    ]
    related_search_vectors = ['musikeralias___fts', 'person___fts']

    class Meta(BaseModel.Meta):
        verbose_name = 'Musiker'
        verbose_name_plural = 'Musiker'
        ordering = ['kuenstler_name']


class MusikerAlias(BaseAliasModel):
    parent = models.ForeignKey('Musiker', models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('alias', 'B', 'simple'),
        ]
    )


class MusikerURL(AbstractURLModel):
    brochure = models.ForeignKey('Musiker', models.CASCADE, related_name='urls')


class Genre(BaseModel):
    genre = models.CharField('Genre', max_length=100, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('genre', 'A', 'simple'),
        ]
    )

    create_field = 'genre'
    name_field = 'genre'
    primary_search_fields = ['genre']
    search_fields = ['genre', 'genrealias__alias']
    related_search_vectors = ['genrealias___fts']

    class Meta(BaseModel.Meta):
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['genre']


class GenreAlias(BaseAliasModel):
    parent = models.ForeignKey('Genre', models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('alias', 'B', 'simple'),
        ]
    )


class Band(BaseModel):
    band_name = models.CharField('Bandname', max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Band')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('Genre')
    musiker = models.ManyToManyField('Musiker')
    orte = models.ManyToManyField('Ort')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('band_name', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ],
        blank=True, null=True, editable=False
    )

    create_field = 'band_name'
    name_field = 'band_name'
    primary_search_fields = ['band_name']
    search_fields = ['band_name', 'bandalias__alias', 'beschreibung', 'bemerkungen']
    related_search_vectors = ['bandalias___fts']

    class Meta(BaseModel.Meta):
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'
        ordering = ['band_name']


class BandAlias(BaseAliasModel):
    parent = models.ForeignKey('Band', models.CASCADE)

    _fts = SearchVectorField(
        columns=[WeightedColumn('alias', 'B', 'simple')],
    )


class BandURL(AbstractURLModel):
    brochure = models.ForeignKey('Band', models.CASCADE, related_name='urls')


class Autor(ComputedNameModel):
    kuerzel = models.CharField('Kürzel', max_length=8, blank=True)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Autors')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    person = models.ForeignKey('Person', models.SET_NULL, null=True, blank=True)

    magazin = models.ManyToManyField('Magazin')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('_name', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_composing_fields = ['person___name', 'kuerzel']
    primary_search_fields = ['_name']
    search_fields = ['_name', 'beschreibung', 'bemerkungen']
    related_search_vectors = ['person___fts']

    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Autor'
        verbose_name_plural = 'Autoren'

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
        person_name = kuerzel = ''
        if 'kuerzel' in data:
            kuerzel = data['kuerzel'][0]
        if 'person___name' in data:
            person_name = data['person___name'][0]
            # The person_name should not be a default value:
            # noinspection PyUnresolvedReferences,PyProtectedMember
            person_default = Person._name_default % {
                'verbose_name': Person._meta.verbose_name
            }
            if person_name in (person_default, 'unbekannt'):
                # person_name is a default value:
                # ('unbekannt' used to be the default for person__nachname)
                person_name = ''

        if person_name:
            if kuerzel:
                return "{} ({})".format(person_name, kuerzel)
            else:
                return person_name
        else:
            # noinspection PyUnresolvedReferences
            opts = cls._meta
            return kuerzel or cls._name_default % {'verbose_name': opts.verbose_name}


class AutorURL(AbstractURLModel):
    brochure = models.ForeignKey('Autor', models.CASCADE, related_name='urls')


class Ausgabe(ComputedNameModel):
    UNBEARBEITET = 'unb'
    INBEARBEITUNG = 'iB'
    ABGESCHLOSSEN = 'abg'
    KEINEBEARBEITUNG = 'kB'
    STATUS_CHOICES = [
        (UNBEARBEITET, 'unbearbeitet'), (INBEARBEITUNG, 'in Bearbeitung'),
        (ABGESCHLOSSEN, 'abgeschlossen'), (KEINEBEARBEITUNG, 'keine Bearbeitung vorgesehen')
    ]

    status = models.CharField(
        'Bearbeitungsstatus', max_length=40, choices=STATUS_CHOICES, default=UNBEARBEITET
    )
    e_datum = models.DateField(
        'Erscheinungsdatum', null=True, blank=True,
        help_text='Format: TT.MM.JJJJ oder JJJJ-MM-TT (ISO 8601)'
    )
    jahrgang = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Jahrgang", validators=[MinValueValidator(1)]
    )
    sonderausgabe = models.BooleanField('Sonderausgabe', default=False)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Ausgabe')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    magazin = models.ForeignKey('Magazin', models.PROTECT)

    audio = models.ManyToManyField('Audio')
    video = models.ManyToManyField('Video')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('_name', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_composing_fields = [
        'beschreibung', 'sonderausgabe', 'e_datum', 'jahrgang',
        'magazin__ausgaben_merkmal', 'ausgabejahr__jahr', 'ausgabenum__num',
        'ausgabelnum__lnum', 'ausgabemonat__monat__abk'
    ]
    primary_search_fields = ['_name']
    search_fields = ['_name', 'beschreibung', 'bemerkungen']

    objects = AusgabeQuerySet.as_manager()

    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Ausgabe'
        verbose_name_plural = 'Ausgaben'
        ordering = ['magazin']

    @classmethod
    def _get_name(cls, **data: tuple) -> str:
        """
        Construct a name from the data given.

        Args:
             **data: mapping of field_path: tuple of values provided by
              MIZQuerySet.values_dict
        """
        beschreibung = ''
        if 'beschreibung' in data:
            beschreibung = concat_limit(
                data['beschreibung'][0].split(),
                width=LIST_DISPLAY_MAX_LEN + 5,
                sep=" "
            )
        if 'sonderausgabe' in data and data['sonderausgabe'][0] and beschreibung:
            # Special issues may be a bit... 'special' in their numerical values.
            # Just use the 'beschreibung' for such an issue.
            return beschreibung

        jahre = jahrgang = ''
        if 'jahrgang' in data:
            jahrgang = data['jahrgang'][0]
        if 'ausgabejahr__jahr' in data:
            # Concatenate the years given.
            # Use four digits for the first year,
            # use only the last two digits for the rest.
            jahre = [  # type: ignore[assignment]
                str(jahr)[2:] if i else str(jahr)
                for i, jahr in enumerate(sorted(data['ausgabejahr__jahr']))
            ]
            jahre = concat_limit(jahre, sep="/")
        if not jahre:
            # Use 'jahrgang' as a fallback or resort to 'k.A.'.
            if jahrgang:
                jahre = "Jg. {}".format(jahrgang)
            else:
                jahre = "k.A."

        e_datum = nums = lnums = monate = ''
        if 'e_datum' in data:
            e_datum = data['e_datum'][0]
        if 'ausgabenum__num' in data:
            nums = concat_limit(
                sorted(data['ausgabenum__num']),
                sep="/",
                z=2
            )
        if 'ausgabelnum__lnum' in data:
            lnums = concat_limit(
                sorted(data['ausgabelnum__lnum']),
                sep="/",
                z=2
            )
        if 'ausgabemonat__monat__abk' in data:
            monat_ordering = [
                'Jan', 'Feb', 'Mrz', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep',
                'Okt', 'Nov', 'Dez'
            ]
            # Sort the month abbreviations according to the calendar.
            monate = sorted(  # type: ignore[assignment]
                data['ausgabemonat__monat__abk'],
                key=lambda abk: monat_ordering.index(abk) + 1 if abk in monat_ordering else 0
            )
            monate = concat_limit(monate, sep="/")
        # 'ausgaben_merkmal' acts as an override to what attribute should make
        # up the name. If that attribute is in data, use that directly.
        merkmal = ''
        if 'magazin__ausgaben_merkmal' in data:
            merkmal = data['magazin__ausgaben_merkmal'][0]
        if merkmal:
            if merkmal == 'e_datum' and e_datum:
                return str(e_datum)
            elif merkmal == 'monat' and monate:
                return "{}-{}".format(jahre, monate)
            elif merkmal == 'lnum' and lnums:
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
        return cls._name_default % {'verbose_name': opts.verbose_name}


class AusgabeJahr(BaseModel):
    jahr = YearField('Jahr')

    ausgabe = models.ForeignKey('Ausgabe', models.CASCADE)

    search_fields = ['jahr']

    class Meta(BaseModel.Meta):
        verbose_name = 'Jahr'
        verbose_name_plural = 'Jahre'
        unique_together = ('jahr', 'ausgabe')
        ordering = ['jahr']


class AusgabeNum(BaseModel):
    num = models.PositiveSmallIntegerField('Nummer')

    ausgabe = models.ForeignKey('Ausgabe', models.CASCADE)

    search_fields = ['num']

    class Meta(BaseModel.Meta):
        verbose_name = 'Nummer'
        verbose_name_plural = 'Ausgabennummer'
        unique_together = ('num', 'ausgabe')
        ordering = ['num']


class AusgabeLnum(BaseModel):
    lnum = models.PositiveSmallIntegerField('Lfd. Nummer')

    ausgabe = models.ForeignKey('Ausgabe', models.CASCADE)

    search_fields = ['lnum']

    class Meta(BaseModel.Meta):
        verbose_name = 'lfd. Nummer'
        verbose_name_plural = 'Laufende Nummer'
        unique_together = ('lnum', 'ausgabe')
        ordering = ['lnum']


class AusgabeMonat(BaseModel):
    ausgabe = models.ForeignKey('Ausgabe', models.CASCADE)
    monat = models.ForeignKey('Monat', models.CASCADE)

    search_fields = ['monat__monat', 'monat__abk']

    class Meta(BaseModel.Meta):
        verbose_name = 'Ausgabe-Monat'
        verbose_name_plural = 'Ausgabe-Monate'
        unique_together = ('ausgabe', 'monat')
        ordering = ['monat']

    def __str__(self) -> str:
        # noinspection PyUnresolvedReferences
        return self.monat.abk


class Monat(BaseModel):
    monat = models.CharField('Monat', max_length=200)
    abk = models.CharField('Abk', max_length=200)
    ordinal = models.PositiveSmallIntegerField(editable=False)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('monat', 'A', 'simple'),
            WeightedColumn('abk', 'A', 'simple')
        ]
    )

    search_fields = ['monat', 'abk', 'ordinal']

    class Meta(BaseModel.Meta):
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        ordering = ['ordinal']

    def __str__(self) -> str:
        return str(self.monat)


class Magazin(BaseModel):
    NUM = 'num'
    LNUM = 'lnum'
    MONAT = 'monat'
    E_DATUM = 'e_datum'
    MERKMAL_CHOICES = [
        (NUM, 'Nummer'), (LNUM, 'Lfd.Nummer'), (MONAT, 'Monat'), (E_DATUM, 'Ersch.Datum')
    ]

    magazin_name = models.CharField('Magazin', max_length=200)
    ausgaben_merkmal = models.CharField(
        'Ausgaben Merkmal', max_length=8, blank=True, choices=MERKMAL_CHOICES,
        help_text=(
            'Das dominante Merkmal der Ausgaben. Diese Angabe bestimmt die '
            'Darstellung der Ausgaben in der Änderungsliste.'
        )
    )
    fanzine = models.BooleanField('Fanzine', default=False)
    issn = ISSNField(
        'ISSN', blank=True,
        help_text='EAN (Barcode Nummer) Angaben erlaubt. Die ISSN wird dann daraus ermittelt.'
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Magazines')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('Genre')
    verlag = models.ManyToManyField('Verlag')
    herausgeber = models.ManyToManyField('Herausgeber')
    orte = models.ManyToManyField('Ort')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('magazin_name', 'A', 'simple'),
            WeightedColumn('issn', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    create_field = 'magazin_name'
    name_field = 'magazin_name'
    primary_search_fields = ['magazin_name']
    search_fields = ['magazin_name', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        verbose_name = 'Magazin'
        verbose_name_plural = 'Magazine'
        ordering = ['magazin_name']

    def __str__(self) -> str:
        return str(self.magazin_name)


class MagazinURL(AbstractURLModel):
    magazin = models.ForeignKey('Magazin', models.CASCADE, related_name='urls')


class Verlag(BaseModel):
    verlag_name = models.CharField('Verlag', max_length=200)

    sitz = models.ForeignKey('Ort', models.SET_NULL, null=True, blank=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('verlag_name', 'A', 'simple'),
        ]
    )

    create_field = 'verlag_name'
    name_field = 'verlag_name'
    search_fields = ['verlag_name']

    class Meta(BaseModel.Meta):
        verbose_name = 'Verlag'
        verbose_name_plural = 'Verlage'
        ordering = ['verlag_name', 'sitz']


# TODO: clean up the data of models: ort/land/bland
class Ort(ComputedNameModel):
    stadt = models.CharField(max_length=200, blank=True)

    bland = models.ForeignKey(
        'bundesland', models.SET_NULL, verbose_name='Bundesland', null=True, blank=True
    )
    land = models.ForeignKey('Land', models.PROTECT)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('_name', 'A', 'simple'),
        ]
    )

    name_composing_fields = [
        'stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code'
    ]
    search_fields = ['_name']

    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Ort'
        verbose_name_plural = 'Orte'
        unique_together = ('stadt', 'bland', 'land')
        ordering = ['land', 'bland', 'stadt']

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
        stadt = bundesland = bundesland_code = land = land_code = ''
        if 'stadt' in data:
            stadt = data['stadt'][0]
        if 'bland__bland_name' in data:
            bundesland = data['bland__bland_name'][0]
        if 'bland__code' in data:
            bundesland_code = data['bland__code'][0]
        if 'land__land_name' in data:
            land = data['land__land_name'][0]
        if 'land__code' in data:
            land_code = data['land__code'][0]

        result_template = "{}, {}"
        if stadt:
            if bundesland_code:
                codes = land_code + '-' + bundesland_code
                return result_template.format(stadt, codes)
            else:
                return result_template.format(stadt, land_code)
        else:
            if bundesland:
                return result_template.format(bundesland, land_code)
            else:
                return land


class Bundesland(BaseModel):
    bland_name = models.CharField('Bundesland', max_length=200)
    code = models.CharField(max_length=4, unique=False)

    land = models.ForeignKey('Land', models.PROTECT)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('bland_name', 'A', 'simple'),
            WeightedColumn('code', 'A', 'simple')
        ]
    )

    name_field = 'bland_name'
    primary_search_fields = []  # type: ignore[var-annotated]
    search_fields = ['bland_name', 'code']

    def __str__(self) -> str:
        return "{} {}".format(self.bland_name, self.code).strip()

    class Meta(BaseModel.Meta):
        verbose_name = 'Bundesland'
        verbose_name_plural = 'Bundesländer'
        unique_together = ('bland_name', 'land')
        ordering = ['land', 'bland_name']


class Land(BaseModel):
    land_name = models.CharField('Land', max_length=100, unique=True)
    code = models.CharField(max_length=4, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('land_name', 'A', 'simple'),
            WeightedColumn('code', 'A', 'simple')
        ]
    )

    name_field = 'land_name'
    search_fields = ['land_name', 'code']

    def __str__(self) -> str:
        return "{} {}".format(self.land_name, self.code).strip()

    class Meta(BaseModel.Meta):
        verbose_name = 'Land'
        verbose_name_plural = 'Länder'
        ordering = ['land_name']


# TODO: make schlagwort 'view-only' in admin (meta.default_permissions)
class Schlagwort(BaseModel):
    schlagwort = models.CharField(max_length=100, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('schlagwort', 'A', 'simple'),
        ]
    )

    create_field = 'schlagwort'
    name_field = 'schlagwort'
    primary_search_fields = []  # type: ignore[var-annotated]
    search_fields = ['schlagwort', 'schlagwortalias__alias']
    related_search_vectors = ['schlagwortalias___fts']

    class Meta(BaseModel.Meta):
        verbose_name = 'Schlagwort'
        verbose_name_plural = 'Schlagwörter'
        ordering = ['schlagwort']


class SchlagwortAlias(BaseAliasModel):
    parent = models.ForeignKey('Schlagwort', models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('alias', 'A', 'simple'),
        ]
    )


class Artikel(BaseModel):
    F = 'f'
    FF = 'ff'
    SU_CHOICES = [(F, 'f'), (FF, 'ff')]

    schlagzeile = models.CharField(max_length=200)
    seite = models.PositiveSmallIntegerField()
    seitenumfang = models.CharField(
        max_length=3, blank=True, choices=SU_CHOICES, default='',
        help_text='Zwei Seiten: f; mehr als zwei Seiten: ff.'
    )
    zusammenfassung = models.TextField(blank=True)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Artikels')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    ausgabe = models.ForeignKey('Ausgabe', models.PROTECT)

    autor = models.ManyToManyField('Autor')
    musiker = models.ManyToManyField('Musiker')
    band = models.ManyToManyField('Band')
    schlagwort = models.ManyToManyField('Schlagwort')
    genre = models.ManyToManyField('Genre')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')
    person = models.ManyToManyField('Person')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('schlagzeile', 'A', 'simple'),
            WeightedColumn('zusammenfassung', 'B', 'german'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'schlagzeile'
    primary_search_fields = ['schlagzeile']
    search_fields = ['schlagzeile', 'zusammenfassung', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        verbose_name = 'Artikel'
        verbose_name_plural = 'Artikel'
        ordering = [
            # TODO: ordering by ausgabe___name doesn't work well when name
            # contains months (1970-Dez comes before 1970-Nov).
            # (might be a PRO for introducing an order column on Ausgabe?)
            'ausgabe__magazin__magazin_name', 'ausgabe___name', 'seite',
            'schlagzeile'
        ]

    def __str__(self) -> str:
        if self.schlagzeile:
            return str(self.schlagzeile)
        elif self.zusammenfassung:
            return str(self.zusammenfassung)
        else:
            return 'Keine Schlagzeile gegeben!'


class Buch(BaseModel):
    # TODO: übersetzer feld
    titel = models.CharField(max_length=200)
    titel_orig = models.CharField('Titel (Original)', max_length=200, blank=True)
    seitenumfang = models.PositiveSmallIntegerField(blank=True, null=True)  # TODO: Semantik: Seitenanzahl?  # noqa
    jahr = YearField('Jahr', null=True, blank=True)
    jahr_orig = YearField('Jahr (Original)', null=True, blank=True)
    auflage = models.CharField(max_length=200, blank=True)
    EAN = EANField(blank=True)
    ISBN = ISBNField(blank=True)
    is_buchband = models.BooleanField(
        default=False, verbose_name='Ist Sammelband',
        help_text='Dieses Buch ist ein Sammelband bestehend aus Aufsätzen.'
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Buches')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    schriftenreihe = models.ForeignKey('Schriftenreihe', models.SET_NULL, null=True, blank=True)
    buchband = models.ForeignKey(
        'self', models.PROTECT, null=True, blank=True, limit_choices_to={'is_buchband': True},
        related_name='buch_set', help_text='Der Sammelband, der diesen Aufsatz enthält.',
        verbose_name='Sammelband',
    )
    sprache = models.CharField(max_length=200, blank=True)

    autor = models.ManyToManyField('Autor')
    musiker = models.ManyToManyField('Musiker')
    band = models.ManyToManyField('Band')
    schlagwort = models.ManyToManyField('Schlagwort')
    genre = models.ManyToManyField('Genre')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')
    person = models.ManyToManyField('Person')
    herausgeber = models.ManyToManyField('Herausgeber')
    verlag = models.ManyToManyField('Verlag')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Buch'
        verbose_name_plural = 'Bücher'

    def __str__(self) -> str:
        return str(self.titel)


class Herausgeber(BaseModel):
    herausgeber = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('herausgeber', 'A', 'simple'),
        ]
    )

    name_field = 'herausgeber'
    create_field = 'herausgeber'
    search_fields = ['herausgeber']

    class Meta(BaseModel.Meta):
        ordering = ['herausgeber']
        verbose_name = 'Herausgeber'
        verbose_name_plural = 'Herausgeber'


class Instrument(BaseModel):
    instrument = models.CharField(unique=True, max_length=200)
    kuerzel = models.CharField('Kürzel', max_length=8, blank=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('instrument', 'A', 'simple'),
            WeightedColumn('kuerzel', 'A', 'simple'),
        ]
    )

    name_field = 'instrument'
    primary_search_fields = ['instrument']
    search_fields = ['instrument', 'kuerzel']

    class Meta(BaseModel.Meta):
        ordering = ['instrument', 'kuerzel']
        verbose_name = 'Instrument'
        verbose_name_plural = 'Instrumente'

    def __str__(self) -> str:
        if self.kuerzel:
            return "{} ({})".format(str(self.instrument), str(self.kuerzel))
        return str(self.instrument)


class Audio(BaseModel):
    titel = models.CharField(max_length=200)
    tracks = models.PositiveIntegerField('Anz. Tracks', blank=True, null=True)
    laufzeit = models.DurationField(
        blank=True, null=True,
        help_text='Format: hh:mm:ss. Beispiel Laufzeit von 144 Minuten: 0:144:0.'
    )
    jahr = YearField('Jahr', blank=True, null=True)
    land_pressung = models.ForeignKey(
        'Land', models.PROTECT, blank=True, null=True, verbose_name='Land der Pressung'
    )
    quelle = models.CharField(
        max_length=200, blank=True,
        help_text='Angaben zur Herkunft/Qualität der Aufnahme: z.B. Broadcast, Live, etc.'
    )
    original = models.BooleanField(
        'Originalmaterial', default=False,
        help_text='Ist das vorliegende Material ein Original?'
    )
    plattennummer = models.CharField(max_length=200, blank=True)
    release_id = models.PositiveIntegerField('Release ID (discogs)', blank=True, null=True)
    discogs_url = models.URLField(
        'Link discogs.com', blank=True,
        help_text="Adresse zur discogs.com Seite dieses Objektes."
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Audio Materials')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    medium = models.ForeignKey(
        'AudioMedium', models.PROTECT, blank=True, null=True, verbose_name="Speichermedium",
        help_text="Format des Speichermediums."
    )
    medium_qty = models.PositiveSmallIntegerField(
        'Anzahl', blank=True, null=True, default=1, validators=[MinValueValidator(1)]
    )

    musiker = models.ManyToManyField('Musiker', through=_m2m.m2m_audio_musiker)
    band = models.ManyToManyField('Band')
    schlagwort = models.ManyToManyField('Schlagwort')
    genre = models.ManyToManyField('Genre')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')
    person = models.ManyToManyField('Person')
    plattenfirma = models.ManyToManyField('Plattenfirma')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Audio Material'
        verbose_name_plural = 'Audio Materialien'

    def __str__(self) -> str:
        return str(self.titel)


class AudioMedium(BaseModel):
    medium = models.CharField(max_length=200, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('medium', 'A', 'simple'),
        ]
    )

    create_field = 'medium'
    name_field = 'medium'
    search_fields = ['medium']

    class Meta(BaseModel.Meta):
        verbose_name = 'Audio-Medium'
        verbose_name_plural = 'Audio-Medium'
        ordering = ['medium']


class Plakat(BaseModel):
    titel = models.CharField(max_length=200)
    # TODO: delete model field 'signatur' (it's no longer in use)
    signatur = models.CharField(
        max_length=200, blank=True, null=True, unique=True,
        help_text=(
            'Kürzel bestehend aus Angabe zur Größe und einer 5-stelligen '
            'fortlaufenden Nummer. Z.B.: DINA2-00395'
        )
    )
    size = models.CharField('Größe', max_length=200, blank=True)
    datum = PartialDateField('Zeitangabe')
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Plakates')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    reihe = models.ForeignKey(
        'Bildreihe', models.PROTECT, blank=True, null=True, verbose_name='Bildreihe'
    )

    schlagwort = models.ManyToManyField('Schlagwort')
    genre = models.ManyToManyField('Genre')
    musiker = models.ManyToManyField('Musiker')
    band = models.ManyToManyField('Band')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')
    person = models.ManyToManyField('Person')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('signatur', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Plakat'
        verbose_name_plural = 'Plakate'


class Bildreihe(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('name', 'A', 'simple'),
        ]
    )

    create_field = 'name'
    name_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Bildreihe'
        verbose_name_plural = 'Bildreihen'


class Schriftenreihe(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('name', 'A', 'simple'),
        ]
    )

    create_field = 'name'
    name_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Schriftenreihe'
        verbose_name_plural = 'Schriftenreihen'


class Dokument(BaseModel):
    titel = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Dokumentes')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('Genre')
    schlagwort = models.ManyToManyField('Schlagwort')
    person = models.ManyToManyField('Person')
    band = models.ManyToManyField('Band')
    musiker = models.ManyToManyField('Musiker')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Dokument'
        verbose_name_plural = 'Dokumente'


class Memorabilien(BaseModel):
    titel = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Memorabiliums')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('Genre')
    schlagwort = models.ManyToManyField('Schlagwort')
    person = models.ManyToManyField('Person')
    band = models.ManyToManyField('Band')
    musiker = models.ManyToManyField('Musiker')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        verbose_name = 'Memorabilia'
        verbose_name_plural = 'Memorabilien'
        ordering = ['titel']


class Spielort(BaseModel):
    name = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Spielortes')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    ort = models.ForeignKey('Ort', models.PROTECT)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('name', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'name'
    primary_search_fields = ['name']
    search_fields = ['name', 'spielortalias__alias', 'beschreibung', 'bemerkungen']
    related_search_vectors = ['spielortalias___fts']

    class Meta(BaseModel.Meta):
        verbose_name = 'Spielort'
        verbose_name_plural = 'Spielorte'
        ordering = ['name', 'ort']


class SpielortURL(AbstractURLModel):
    brochure = models.ForeignKey('Spielort', models.CASCADE, related_name='urls')


class SpielortAlias(BaseAliasModel):
    parent = models.ForeignKey('Spielort', models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('alias', 'A', 'simple'),
        ]
    )


class Technik(BaseModel):
    titel = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Technik')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('Genre')
    schlagwort = models.ManyToManyField('Schlagwort')
    person = models.ManyToManyField('Person')
    band = models.ManyToManyField('Band')
    musiker = models.ManyToManyField('Musiker')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Technik'
        verbose_name_plural = 'Technik'
        ordering = ['titel']


class Veranstaltung(BaseModel):
    name = models.CharField(max_length=200)
    datum = PartialDateField(blank=False)

    spielort = models.ForeignKey('Spielort', models.PROTECT)
    reihe = models.ForeignKey('Veranstaltungsreihe', models.PROTECT, blank=True, null=True)

    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Veranstaltung')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    musiker = models.ManyToManyField('Musiker')
    band = models.ManyToManyField('Band')
    schlagwort = models.ManyToManyField('Schlagwort')
    genre = models.ManyToManyField('Genre')
    person = models.ManyToManyField('Person')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('name', 'A', 'simple'),
            WeightedColumn('datum', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'name'
    primary_search_fields = ['name']
    search_fields = [
        'name', 'datum', 'veranstaltungalias__alias', 'beschreibung', 'bemerkungen']
    related_search_vectors = ['veranstaltungalias___fts']

    class Meta(BaseModel.Meta):
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'
        ordering = ['name', 'datum', 'spielort']

    def __str__(self) -> str:
        if isinstance(self.datum, PartialDate):
            date = self.datum.localize()
        else:
            date = str(self.datum)
        return "{} ({})".format(self.name, date)


class VeranstaltungAlias(BaseAliasModel):
    parent = models.ForeignKey('Veranstaltung', models.CASCADE)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('alias', 'A', 'simple'),
        ]
    )


class VeranstaltungURL(AbstractURLModel):
    brochure = models.ForeignKey('Veranstaltung', models.CASCADE, related_name='urls')


class Veranstaltungsreihe(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('name', 'A', 'simple'),
        ]
    )

    create_field = 'name'
    name_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Veranstaltungsreihe'
        verbose_name_plural = 'Veranstaltungsreihen'


class Video(BaseModel):
    titel = models.CharField(max_length=200)
    laufzeit = models.DurationField(
        blank=True, null=True,
        help_text='Format: hh:mm:ss. Beispiel Laufzeit von 144 Minuten: 0:144:0.'
    )
    jahr = YearField('Jahr', blank=True, null=True)
    quelle = models.CharField(
        max_length=200, blank=True,
        help_text='Angaben zur Herkunft/Qualität der Aufnahme: z.B. Broadcast, Live, etc.'
    )
    original = models.BooleanField(
        'Originalmaterial', default=False,
        help_text='Ist das vorliegende Material ein Original?'
    )
    release_id = models.PositiveIntegerField('Release ID (discogs)', blank=True, null=True)
    discogs_url = models.URLField(
        'Link discogs.com', blank=True,
        help_text="Adresse zur discogs.com Seite dieses Objektes."
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Video Materials')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    medium = models.ForeignKey(
        'VideoMedium', models.PROTECT, blank=True, null=True, verbose_name="Speichermedium",
        help_text="Format des Speichermediums."
    )
    medium_qty = models.PositiveSmallIntegerField(
        'Anzahl', blank=True, null=True, default=1, validators=[MinValueValidator(1)]
    )

    musiker = models.ManyToManyField('Musiker', through=_m2m.m2m_video_musiker)
    band = models.ManyToManyField('Band')
    schlagwort = models.ManyToManyField('Schlagwort')
    genre = models.ManyToManyField('Genre')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')
    person = models.ManyToManyField('Person')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        verbose_name = 'Video Material'
        verbose_name_plural = 'Video Materialien'
        ordering = ['titel']


class VideoMedium(BaseModel):
    medium = models.CharField(max_length=200, unique=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('medium', 'A', 'simple'),
        ]
    )

    create_field = 'medium'
    name_field = 'medium'
    search_fields = ['medium']

    class Meta(BaseModel.Meta):
        verbose_name = 'Video-Medium'
        verbose_name_plural = 'Video-Medium'
        ordering = ['medium']


class Provenienz(BaseModel):
    SCHENK = 'Schenkung'
    SPENDE = 'Spende'
    FUND = 'Fund'
    LEIHG = 'Leihgabe'
    DAUERLEIHG = 'Dauerleihgabe'
    TYP_CHOICES = [
        (SCHENK, 'Schenkung'), (SPENDE, 'Spende'), (FUND, 'Fund'),
        (LEIHG, 'Leihgabe'), (DAUERLEIHG, 'Dauerleihgabe')
    ]

    typ = models.CharField(
        'Art der Provenienz', max_length=100, choices=TYP_CHOICES, default=SCHENK
    )

    geber = models.ForeignKey('Geber', models.PROTECT)

    # TODO: FTS SearchVectorField

    search_fields = ['geber__name']

    class Meta(BaseModel.Meta):
        ordering = ['geber', 'typ']
        verbose_name = 'Provenienz'
        verbose_name_plural = 'Provenienzen'

    def __str__(self) -> str:
        return "{0} ({1})".format(str(self.geber.name), str(self.typ))


class Geber(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('name', 'A', 'simple'),
        ]
    )

    name_field = create_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Geber'
        verbose_name_plural = 'Geber'


class Lagerort(ComputedNameModel):
    ort = models.CharField(max_length=200)
    raum = models.CharField(max_length=200, blank=True)
    regal = models.CharField(max_length=200, blank=True)
    fach = models.CharField(max_length=200, blank=True)
    ordner = models.CharField(max_length=200, blank=True)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('_name', 'A', 'simple'),
        ]
    )

    name_composing_fields = ['ort', 'raum', 'regal', 'fach']
    search_fields = ['ort', 'raum', 'regal', 'fach', 'ordner']

    class Meta(BaseModel.Meta):
        verbose_name = 'Lagerort'
        verbose_name_plural = 'Lagerorte'
        ordering = ['_name']

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
        ort = raum = regal = fach = ''
        if 'ort' in data:
            ort = data['ort'][0]
        if 'raum' in data:
            raum = data['raum'][0]
        if 'regal' in data:
            regal = data['regal'][0]
        if 'fach' in data:
            fach = data['fach'][0]

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
    lagerort = models.ForeignKey('Lagerort', models.PROTECT)
    provenienz = models.ForeignKey('Provenienz', models.SET_NULL, blank=True, null=True)

    audio = models.ForeignKey('Audio', models.CASCADE, blank=True, null=True)
    ausgabe = models.ForeignKey('Ausgabe', models.CASCADE, blank=True, null=True)
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, blank=True, null=True)
    buch = models.ForeignKey('Buch', models.CASCADE, blank=True, null=True)
    dokument = models.ForeignKey('Dokument', models.CASCADE, blank=True, null=True)
    foto = models.ForeignKey('Foto', models.CASCADE, blank=True, null=True)
    memorabilien = models.ForeignKey('Memorabilien', models.CASCADE, blank=True, null=True)
    plakat = models.ForeignKey('Plakat', models.CASCADE, blank=True, null=True)
    technik = models.ForeignKey('Technik', models.CASCADE, blank=True, null=True)
    video = models.ForeignKey('Video', models.CASCADE, blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = 'Bestand'
        verbose_name_plural = 'Bestände'
        ordering = ['pk']

    def __str__(self) -> str:
        return str(self.lagerort)

    @property
    def bestand_object(self) -> Optional[models.Model]:
        """Return the archive object this Bestand instance refers to."""
        if hasattr(self, '_bestand_object'):
            return self._bestand_object
        self._bestand_object: Optional[models.Model] = None
        for field in get_model_fields(self, base=False, foreign=True, m2m=False):
            # The archive object is referenced by the one FK relation (other
            # than Lagerort and Provenienz) that is not null.
            # noinspection PyProtectedMember
            if field.related_model._meta.object_name in ('Lagerort', 'Provenienz'):
                continue
            related_obj = getattr(self, field.name)
            if related_obj:
                # noinspection PyProtectedMember
                if related_obj._meta.object_name == 'BaseBrochure':
                    # Handle the multiple inheritance stuff:
                    related_obj = related_obj.resolve_child()
                self._bestand_object = related_obj
        return self._bestand_object


class Datei(BaseModel):
    MEDIA_AUDIO = 'audio'
    MEDIA_BILD = 'bild'
    MEDIA_SONSTIGE = 'sonstige'
    MEDIA_TEXT = 'text'
    MEDIA_VIDEO = 'video'
    MEDIA_TYP_CHOICES = [
        (MEDIA_AUDIO, 'Audio'), (MEDIA_VIDEO, 'Video'), (MEDIA_BILD, 'Bild'),
        (MEDIA_TEXT, 'Text'), (MEDIA_SONSTIGE, 'Sonstige')
    ]

    titel = models.CharField(max_length=200)
    media_typ = models.CharField(
        'Media Typ', max_length=200, choices=MEDIA_TYP_CHOICES,
        default=MEDIA_AUDIO
    )
    datei_media = models.FileField(  # Datei Media Server
        'Datei', blank=True, null=True, editable=False,
        help_text="Datei auf Datenbank-Server hoch- bzw herunterladen."
    )
    datei_pfad = models.CharField(
        'Datei-Pfad', max_length=200, blank=True,
        help_text="Pfad (inklusive Datei-Namen und Endung) zur Datei im gemeinsamen Ordner."
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Datei')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    provenienz = models.ForeignKey('Provenienz', models.SET_NULL, blank=True, null=True)

    genre = models.ManyToManyField('Genre')
    schlagwort = models.ManyToManyField('Schlagwort')
    person = models.ManyToManyField('Person')
    band = models.ManyToManyField('Band')
    musiker = models.ManyToManyField('Musiker', through=_m2m.m2m_datei_musiker)
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Datei'
        verbose_name_plural = 'Dateien'

    def __str__(self) -> str:
        return str(self.titel)


class Plattenfirma(BaseModel):
    name = models.CharField(max_length=200)

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('name', 'A', 'simple'),
        ]
    )

    name_field = create_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Plattenfirma'
        verbose_name_plural = 'Plattenfirmen'


class BrochureYear(AbstractJahrModel):
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, related_name='jahre')


class BrochureURL(AbstractURLModel):
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, related_name='urls')


class BaseBrochure(BaseModel):
    titel = models.CharField(max_length=200)
    zusammenfassung = models.TextField(blank=True)
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    ausgabe = models.ForeignKey(
        'ausgabe', models.SET_NULL, related_name='beilagen',
        verbose_name='Ausgabe', blank=True, null=True
    )

    genre = models.ManyToManyField('Genre')

    # TODO: add full text seach SearchVectorField
    #   Brochure, Kalender, Warenkatalog inherit from BaseBrochure via
    #   multi-table inheritance. This means that fields declared in BaseBrochure
    #   aren't present in the postgres tables of Brochure, etc.
    #   This, in turn, means that these fields cannot immediately be used as
    #   columns for SearchVectorField.

    name_field = 'titel'

    def __str__(self) -> str:
        return str(self.titel)

    def resolve_child(self) -> models.Model:
        """Fetch a child instance from this parent instance."""
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

    class Meta(BaseModel.Meta):
        ordering = ['titel']


class Brochure(BaseBrochure):
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Broschüre')

    schlagwort = models.ManyToManyField('Schlagwort')
    # TODO: add spielort ManyToManyField or merge all the BaseBrochure models?
    # (assuming a Brochure is specifically about a venue/s)

    primary_search_fields = ['titel']
    search_fields = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']

    class Meta(BaseBrochure.Meta):
        verbose_name = 'Broschüre'
        verbose_name_plural = 'Broschüren'


class Kalender(BaseBrochure):
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Programmheftes')

    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    primary_search_fields = ['titel']
    search_fields = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']

    class Meta(BaseBrochure.Meta):
        verbose_name = 'Programmheft'
        verbose_name_plural = 'Programmhefte'


class Katalog(BaseBrochure):
    ART_BUCH = 'buch'
    ART_MERCH = 'merch'
    ART_OTHER = 'other'
    ART_TECH = 'tech'
    ART_TON = 'ton'
    ART_CHOICES = [
        (ART_MERCH, 'Merchandise'), (ART_TECH, 'Instrumente & Technik'),
        (ART_TON, 'Tonträger'), (ART_BUCH, 'Bücher'), (ART_OTHER, 'Anderes')
    ]

    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Kataloges')
    art = models.CharField(
        'Art d. Kataloges', max_length=40, choices=ART_CHOICES, default=ART_MERCH
    )

    primary_search_fields = ['titel']
    search_fields = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']

    class Meta(BaseBrochure.Meta):
        verbose_name = 'Warenkatalog'
        verbose_name_plural = 'Warenkataloge'


class Foto(BaseModel):
    ART_NEGATIV = 'negativ'
    ART_POSITIV = 'positiv'
    ART_REPRINT = 'reprint'
    ART_POLAROID = 'polaroid'
    ART_CHOICES = [
        (ART_NEGATIV, 'negativ'), (ART_POSITIV, 'positiv'),
        (ART_REPRINT, 'Neuabzug (reprint)'), (ART_POLAROID, 'Polaroid')
    ]

    titel = models.CharField(max_length=200)
    size = models.CharField('Größe', max_length=200, blank=True)
    datum = PartialDateField('Zeitangabe')
    typ = models.CharField(
        'Art des Fotos', max_length=100, choices=ART_CHOICES, default=ART_NEGATIV
    )
    farbe = models.BooleanField('Farbfoto')
    owner = models.CharField('Rechteinhaber', max_length=200, blank=True)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Fotos')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    reihe = models.ForeignKey(
        'Bildreihe', models.PROTECT, blank=True, null=True, verbose_name='Bildreihe'
    )

    schlagwort = models.ManyToManyField('Schlagwort')
    genre = models.ManyToManyField('Genre')
    musiker = models.ManyToManyField('Musiker')
    band = models.ManyToManyField('Band')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')
    person = models.ManyToManyField('Person')

    _fts = SearchVectorField(
        columns=[
            WeightedColumn('titel', 'A', 'simple'),
            WeightedColumn('beschreibung', 'C', 'german'),
            WeightedColumn('bemerkungen', 'D', 'simple')
        ]
    )

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'owner', 'beschreibung', 'bemerkungen']

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Foto'
        verbose_name_plural = 'Fotos'
