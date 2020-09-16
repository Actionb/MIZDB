# TODO: Semantik buch.buchband: Einzelbänder/Aufsätze: Teile eines Buchbandes
from django.core.validators import MinValueValidator
from django.db import models

import DBentry.m2m as _m2m
from DBentry.base.models import (
    BaseModel, ComputedNameModel, BaseAliasModel, AbstractJahrModel,
    AbstractURLModel
)
from DBentry.constants import LIST_DISPLAY_MAX_LEN
from DBentry.fields import (
    ISSNField, ISBNField, EANField, YearField, PartialDate, PartialDateField
)
from DBentry.managers import AusgabeQuerySet, HumanNameQuerySet, PeopleQuerySet
from DBentry.utils import concat_limit


class Person(ComputedNameModel):
    vorname = models.CharField(max_length=200, blank=True)
    nachname = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Person')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    orte = models.ManyToManyField('Ort')

    name_composing_fields = ['vorname', 'nachname']
    primary_search_fields = ['_name']
    search_fields = ['_name', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    objects = PeopleQuerySet.as_manager()

    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Person'
        verbose_name_plural = 'Personen'

    @classmethod
    def _get_name(cls, **data):
        """
        Construct a name from the 'data' given.
        'data' is a mapping of field_path: tuple of values provided by
        MIZQuerySet.values_dict.

        Returns a name in the format '{vorname} {nachname}'.
        """
        vorname = nachname = ''
        if 'vorname' in data:
            vorname = data['vorname'][0]
        if 'nachname' in data:
            nachname = data['nachname'][0]
        if vorname or nachname:
            return "{} {}".format(vorname, nachname).strip()
        return cls._name_default % {'verbose_name': cls._meta.verbose_name}


class Musiker(BaseModel):
    kuenstler_name = models.CharField('Künstlername', max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Musikers')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    person = models.ForeignKey('Person', models.SET_NULL, null=True, blank=True)

    genre = models.ManyToManyField('Genre', through=_m2m.m2m_musiker_genre)
    instrument = models.ManyToManyField('Instrument', through=_m2m.m2m_musiker_instrument)
    orte = models.ManyToManyField('Ort')

    create_field = 'kuenstler_name'
    name_field = 'kuenstler_name'
    primary_search_fields = ['kuenstler_name']
    search_fields = ['kuenstler_name', 'musikeralias__alias', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {
        'musikeralias__alias': 'Alias',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen'
    }

    objects = HumanNameQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        verbose_name = 'Musiker'
        verbose_name_plural = 'Musiker'
        ordering = ['kuenstler_name']
class MusikerAlias(BaseAliasModel):
    parent = models.ForeignKey('Musiker', models.CASCADE)


class Genre(BaseModel):
    genre = models.CharField('Genre', max_length=100, unique=True)

    create_field = 'genre'
    name_field = 'genre'
    primary_search_fields = ['genre']
    search_fields = ['genre', 'genrealias__alias']
    search_fields_suffixes = {
        'genrealias__alias': 'Alias'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['genre']
class GenreAlias(BaseAliasModel):
    parent = models.ForeignKey('Genre', models.CASCADE)


class Band(BaseModel):
    band_name = models.CharField('Bandname', max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Band')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('Genre', through=_m2m.m2m_band_genre)
    musiker = models.ManyToManyField('Musiker', through=_m2m.m2m_band_musiker)
    orte = models.ManyToManyField('Ort')

    create_field = 'band_name'
    name_field = 'band_name'
    primary_search_fields = ['band_name']
    search_fields = ['band_name', 'bandalias__alias', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {
        'bandalias__alias': 'Alias',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'
        ordering = ['band_name']
class BandAlias(BaseAliasModel):
    parent = models.ForeignKey('Band', models.CASCADE)


class Autor(ComputedNameModel):
    kuerzel = models.CharField('Kürzel', max_length=8, blank=True)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Autors')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    person = models.ForeignKey('Person', models.SET_NULL, null=True, blank=True)

    magazin = models.ManyToManyField('Magazin', through=_m2m.m2m_autor_magazin)

    name_composing_fields = ['person___name', 'kuerzel']
    primary_search_fields = ['_name']
    search_fields = ['_name', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    objects = PeopleQuerySet.as_manager()

    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Autor'
        verbose_name_plural = 'Autoren'

    @classmethod
    def _get_name(cls, **data):
        """
        Construct a name from the 'data' given.
        'data' is a mapping of field_path: tuple of values provided by
        MIZQuerySet.values_dict.

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
            return kuerzel or cls._name_default % {'verbose_name': cls._meta.verbose_name}


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
        'Bearbeitungsstatus', max_length=40, choices=STATUS_CHOICES, default=UNBEARBEITET)
    e_datum = models.DateField(
        'Erscheinungsdatum', null=True, blank=True, help_text='Format: tt.mm.jjjj')
    jahrgang = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Jahrgang", validators=[MinValueValidator(1)])
    sonderausgabe = models.BooleanField('Sonderausgabe', default=False)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Ausgabe')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    magazin = models.ForeignKey('Magazin', models.PROTECT)

    audio = models.ManyToManyField('Audio', through=_m2m.m2m_audio_ausgabe)

    name_composing_fields = [
        'beschreibung', 'sonderausgabe', 'e_datum', 'jahrgang',
        'magazin__ausgaben_merkmal', 'ausgabejahr__jahr', 'ausgabenum__num',
        'ausgabelnum__lnum', 'ausgabemonat__monat__abk'
    ]
    primary_search_fields = ['_name']
    search_fields = ['_name', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    objects = AusgabeQuerySet.as_manager()

    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Ausgabe'
        verbose_name_plural = 'Ausgaben'
        ordering = ['magazin']
        permissions = [
            ('alter_bestand_ausgabe', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]

    @classmethod
    def _get_name(cls, **data):
        """
        Construct a name from the 'data' given.
        'data' is a mapping of field_path: tuple of values provided by
        MIZQuerySet.values_dict.
        """
        beschreibung = ''
        if 'beschreibung' in data:
            beschreibung = concat_limit(
                data['beschreibung'][0].split(),
                width=LIST_DISPLAY_MAX_LEN + 5,
                sep=" "
            )
        if ('sonderausgabe' in data and data['sonderausgabe'][0] and beschreibung):
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
            jahre = [
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
            monate = sorted(
                data['ausgabemonat__monat__abk'],
                key=lambda abk:
                    monat_ordering.index(abk) + 1 if abk in monat_ordering else 0
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
        return cls._name_default % {'verbose_name': cls._meta.verbose_name}


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

    def __str__(self):
        return self.monat.abk


class Monat(BaseModel):
    monat = models.CharField('Monat', max_length=200)
    abk = models.CharField('Abk', max_length=200)
    ordinal = models.PositiveSmallIntegerField(editable=False)

    search_fields = ['monat', 'abk', 'ordinal']

    class Meta(BaseModel.Meta):
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        ordering = ['ordinal']

    def __str__(self):
        return self.monat


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
        help_text=('Das dominante Merkmal der Ausgaben. Diese Angabe bestimmt die Darstellung der '
            'Ausgaben in der Änderungsliste.')
    )
    fanzine = models.BooleanField('Fanzine', default=False)
    issn = ISSNField(
        'ISSN', blank=True,
        help_text='EAN (Barcode Nummer) Angaben erlaubt. Die ISSN wird dann daraus ermittelt.'
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Magazines')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('Genre', through=_m2m.m2m_magazin_genre)
    verlag = models.ManyToManyField('Verlag', through=_m2m.m2m_magazin_verlag)
    herausgeber = models.ManyToManyField('Herausgeber', through=_m2m.m2m_magazin_herausgeber)
    orte = models.ManyToManyField('Ort')

    create_field = 'magazin_name'
    name_field = 'magazin_name'
    primary_search_fields = ['magazin_name']
    search_fields = ['magazin_name', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Magazin'
        verbose_name_plural = 'Magazine'
        ordering = ['magazin_name']

    def __str__(self):
        return str(self.magazin_name)

class MagazinURL(AbstractURLModel):
    magazin = models.ForeignKey('Magazin', models.CASCADE, related_name='urls')


class Verlag(BaseModel):
    verlag_name = models.CharField('Verlag', max_length=200)

    sitz = models.ForeignKey('Ort', models.SET_NULL, null=True, blank=True)

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
    def _get_name(cls, **data):
        """
        Construct a name from the 'data' given.
        'data' is a mapping of field_path: tuple of values provided by
        MIZQuerySet.values_dict.

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

        rslt_template = "{}, {}"
        if stadt:
            if bundesland_code:
                codes = land_code + '-' + bundesland_code
                return rslt_template.format(stadt, codes)
            else:
                return rslt_template.format(stadt, land_code)
        else:
            if bundesland:
                return rslt_template.format(bundesland, land_code)
            else:
                return land


class Bundesland(BaseModel):
    bland_name = models.CharField('Bundesland', max_length=200)
    code = models.CharField(max_length=4, unique=False)

    land = models.ForeignKey('Land', models.PROTECT)

    name_field = 'bland_name'
    primary_search_fields = []
    search_fields = ['bland_name', 'code']
    search_fields_suffixes = {
        'code': 'Bundesland-Code'
    }

    def __str__(self):
        return "{} {}".format(self.bland_name, self.code).strip()

    class Meta(BaseModel.Meta):
        verbose_name = 'Bundesland'
        verbose_name_plural = 'Bundesländer'
        unique_together = ('bland_name', 'land')
        ordering = ['land', 'bland_name']


class Land(BaseModel):
    land_name = models.CharField('Land', max_length=100, unique=True)
    code = models.CharField(max_length=4, unique=True)

    name_field = 'land_name'
    search_fields = ['land_name', 'code']
    search_fields_suffixes = {'code': 'Land-Code'}

    def __str__(self):
        return "{} {}".format(self.land_name, self.code).strip()

    class Meta(BaseModel.Meta):
        verbose_name = 'Land'
        verbose_name_plural = 'Länder'
        ordering = ['land_name']

# TODO: make schlagwort 'view-pnly' in admin (meta.default_permissions)
class Schlagwort(BaseModel):
    schlagwort = models.CharField(max_length=100, unique=True)

    create_field = 'schlagwort'
    name_field = 'schlagwort'
    primary_search_fields = []
    search_fields = ['schlagwort', 'schlagwortalias__alias']
    search_fields_suffixes = {'schlagwortalias__alias': 'Alias'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Schlagwort'
        verbose_name_plural = 'Schlagwörter'
        ordering = ['schlagwort']
class SchlagwortAlias(BaseAliasModel):
    parent = models.ForeignKey('Schlagwort', models.CASCADE)


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

    genre = models.ManyToManyField('Genre', through=_m2m.m2m_artikel_genre)
    schlagwort = models.ManyToManyField('Schlagwort', through=_m2m.m2m_artikel_schlagwort)
    person = models.ManyToManyField('Person', through=_m2m.m2m_artikel_person)
    autor = models.ManyToManyField('Autor', through=_m2m.m2m_artikel_autor)
    band = models.ManyToManyField('Band', through=_m2m.m2m_artikel_band)
    musiker = models.ManyToManyField('Musiker', through=_m2m.m2m_artikel_musiker)
    ort = models.ManyToManyField('Ort', through=_m2m.m2m_artikel_ort)
    spielort = models.ManyToManyField('Spielort', through=_m2m.m2m_artikel_spielort)
    veranstaltung = models.ManyToManyField('Veranstaltung', through=_m2m.m2m_artikel_veranstaltung)

    name_field = 'schlagzeile'
    primary_search_fields = ['schlagzeile']
    search_fields = ['schlagzeile', 'zusammenfassung', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {
        'zusammenfassung': 'Zusammenfassung',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Artikel'
        verbose_name_plural = 'Artikel'
        ordering = [
            'ausgabe__magazin__magazin_name', 'ausgabe___name', 'seite',
            'schlagzeile'
        ]

    def __str__(self):
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
    seitenumfang = models.PositiveSmallIntegerField(blank=True, null=True)  # TODO: Semantik: Seitenanzahl?
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

    herausgeber = models.ManyToManyField('Herausgeber')
    verlag = models.ManyToManyField('Verlag')
    autor = models.ManyToManyField('Autor')
    genre = models.ManyToManyField('Genre')
    schlagwort = models.ManyToManyField('Schlagwort')
    person = models.ManyToManyField('Person')
    band = models.ManyToManyField('Band')
    musiker = models.ManyToManyField('Musiker')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Buch'
        verbose_name_plural = 'Bücher'
        permissions = [
            ('alter_bestand_buch', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]

    def __str__(self):
        return str(self.titel)


class Herausgeber(BaseModel):
    herausgeber = models.CharField(max_length=200)

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

    name_field = 'instrument'
    primary_search_fields = ['instrument']
    search_fields = ['instrument', 'kuerzel']
    search_fields_suffixes = {'kuerzel': 'Kürzel'}

    class Meta(BaseModel.Meta):
        ordering = ['instrument', 'kuerzel']
        verbose_name = 'Instrument'
        verbose_name_plural = 'Instrumente'

    def __str__(self):
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
    e_jahr = YearField('Jahr', blank=True, null=True)
    quelle = models.CharField(max_length=200, blank=True, help_text='Broadcast, Live, etc.')
    # TODO: field 'catalog_nr' is missing in AudioAdmin -- Format.catalog_nr does that job??
    catalog_nr = models.CharField('Katalog Nummer', max_length=200, blank=True)
    release_id = models.PositiveIntegerField('Release ID (discogs)', blank=True, null=True)
    discogs_url = models.URLField(
        'Link discogs.com', blank=True,
        help_text="Adresse zur discogs.com Seite dieses Objektes."
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Audio Materials')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    plattenfirma = models.ManyToManyField('Plattenfirma', through=_m2m.m2m_audio_plattenfirma)
    band = models.ManyToManyField('Band', through=_m2m.m2m_audio_band)
    genre = models.ManyToManyField('Genre', through=_m2m.m2m_audio_genre)
    musiker = models.ManyToManyField('Musiker', through=_m2m.m2m_audio_musiker)
    person = models.ManyToManyField('Person', through=_m2m.m2m_audio_person)
    schlagwort = models.ManyToManyField('Schlagwort', through=_m2m.m2m_audio_schlagwort)
    spielort = models.ManyToManyField('Spielort', through=_m2m.m2m_audio_spielort)
    veranstaltung = models.ManyToManyField('Veranstaltung', through=_m2m.m2m_audio_veranstaltung)
    ort = models.ManyToManyField('Ort', through=_m2m.m2m_audio_ort)

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Audio Material'
        verbose_name_plural = 'Audio Materialien'
        permissions = [
            ('alter_bestand_audio', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]

    def __str__(self):
        return str(self.titel)


class Bildmaterial(BaseModel):
    titel = models.CharField(max_length=200)
    signatur = models.CharField(
        max_length=200, blank=True, null=True, unique=True,
        help_text=('Kürzel bestehend aus Angabe zur Größe und '
            'einer 5-stelligen fortlaufenden Nummer. Z.B.: DINA2-00395')
    )
    size = models.CharField('Größe', max_length=200, blank=True)
    datum = PartialDateField('Zeitangabe')
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Bildmaterials')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    reihe = models.ForeignKey(
        'Bildreihe', models.PROTECT, blank=True, null=True, verbose_name='Bildreihe')

    genre = models.ManyToManyField('Genre')
    schlagwort = models.ManyToManyField('Schlagwort')
    person = models.ManyToManyField('Person')
    band = models.ManyToManyField('Band')
    musiker = models.ManyToManyField('Musiker')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Bild Material'
        verbose_name_plural = 'Bild Materialien'
        permissions = [
            ('alter_bestand_bildmaterial', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class Bildreihe(BaseModel):
    name = models.CharField(max_length=200)

    create_field = 'name'
    name_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Bildreihe'
        verbose_name_plural = 'Bildreihen'


class Schriftenreihe(BaseModel):
    name = models.CharField(max_length=200)

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

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Dokument'
        verbose_name_plural = 'Dokumente'
        permissions = [
            ('alter_bestand_dokument', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


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

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Memorabilia'
        verbose_name_plural = 'Memorabilien'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_memorabilien', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class Spielort(BaseModel):
    name = models.CharField(max_length=200)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Spielortes')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    ort = models.ForeignKey('Ort', models.PROTECT)

    name_field = 'name'
    primary_search_fields = ['name']
    search_fields = ['name', 'spielortalias__alias', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {
        'spielortalias__alias': 'Alias',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Spielort'
        verbose_name_plural = 'Spielorte'
        ordering = ['name', 'ort']
class SpielortAlias(BaseAliasModel):
    parent = models.ForeignKey('Spielort', models.CASCADE)


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

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Technik'
        verbose_name_plural = 'Technik'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_technik', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class Veranstaltung(BaseModel):
    name = models.CharField(max_length=200)
    datum = PartialDateField(blank=False)

    spielort = models.ForeignKey('Spielort', models.PROTECT)
    reihe = models.ForeignKey('Veranstaltungsreihe', models.PROTECT, blank=True, null=True)

    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Veranstaltung')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('Genre')
    person = models.ManyToManyField('Person')
    band = models.ManyToManyField('Band')
    schlagwort = models.ManyToManyField('Schlagwort')
    musiker = models.ManyToManyField('Musiker')

    name_field = 'name'
    primary_search_fields = ['name']
    search_fields = [
        'name', 'datum', 'veranstaltungalias__alias', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {
        'veranstaltungalias__alias': 'Alias',
        'datum': 'Datum',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'
        ordering = ['name', 'datum', 'spielort']

    def __str__(self):
        if isinstance(self.datum, PartialDate):
            date = self.datum.localize()
        else:
            date = str(self.datum)
        return "{} ({})".format(self.name, date)
class VeranstaltungAlias(BaseAliasModel):
    parent = models.ForeignKey('Veranstaltung', models.CASCADE)


class Veranstaltungsreihe(BaseModel):
    name = models.CharField(max_length=200)

    create_field = 'name'
    name_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Veranstaltungsreihe'
        verbose_name_plural = 'Veranstaltungsreihen'


class Video(BaseModel):
    titel = models.CharField(max_length=200)
    tracks = models.PositiveSmallIntegerField('Anz. Tracks', blank=True, null=True)
    laufzeit = models.DurationField(
        blank=True, null=True,
        help_text='Format: hh:mm:ss. Beispiel Laufzeit von 144 Minuten: 0:144:0.'
    )
    jahr = YearField('Jahr', blank=True, null=True)
    quelle = models.CharField(max_length=200, blank=True, help_text='Broadcast, Live, etc.')
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Video Materials')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    medium = models.ForeignKey(
        'VideoMedium', models.PROTECT, blank=True, null=True, verbose_name="Medium",
        help_text="Format des Speichermediums."
    )

    band = models.ManyToManyField('Band')
    genre = models.ManyToManyField('Genre')
    musiker = models.ManyToManyField('Musiker', through=_m2m.m2m_video_musiker)
    person = models.ManyToManyField('Person')
    schlagwort = models.ManyToManyField('Schlagwort')
    ort = models.ManyToManyField('Ort')
    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Video Material'
        verbose_name_plural = 'Video Materialien'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_video', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class VideoMedium(BaseModel):
    medium = models.CharField(max_length=200)

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

    search_fields = ['geber__name']

    class Meta(BaseModel.Meta):
        ordering = ['geber', 'typ']
        verbose_name = 'Provenienz'
        verbose_name_plural = 'Provenienzen'

    def __str__(self):
        return "{0} ({1})".format(str(self.geber.name), str(self.typ))


class Geber(BaseModel):
    name = models.CharField(max_length=200)

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

    name_composing_fields = ['ort', 'raum', 'regal', 'fach']
    search_fields = ['ort', 'raum', 'regal', 'fach', 'ordner']
    search_fields_suffixes = {'raum': 'Raum', 'regal': 'Regal', 'fach': 'Fach', 'ordner': 'Ordner'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Lagerort'
        verbose_name_plural = 'Lagerorte'
        ordering = ['_name']

    @classmethod
    def _get_name(cls, **data):
        """
        Construct a name from the 'data' given.
        'data' is a mapping of field_path: tuple of values provided by
        MIZQuerySet.values_dict.

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
    BESTAND_CHOICES = [
        ('audio', 'Audio'), ('ausgabe', 'Ausgabe'), ('bildmaterial', 'Bildmaterial'),
        ('buch', 'Buch'), ('dokument', 'Dokument'), ('memorabilien', 'Memorabilien'),
        ('technik', 'Technik'), ('video', 'Video')
    ]

    signatur = models.AutoField(primary_key=True)
    bestand_art = models.CharField(
        'Bestand-Art', max_length=20, choices=BESTAND_CHOICES, blank=False, default='ausgabe')

    lagerort = models.ForeignKey('Lagerort', models.PROTECT)
    provenienz = models.ForeignKey('Provenienz', models.SET_NULL, blank=True, null=True)

    audio = models.ForeignKey('Audio', models.CASCADE, blank=True, null=True)
    ausgabe = models.ForeignKey('Ausgabe', models.CASCADE, blank=True, null=True)
    bildmaterial = models.ForeignKey('Bildmaterial', models.CASCADE, blank=True, null=True)
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, blank=True, null=True)
    buch = models.ForeignKey('Buch', models.CASCADE, blank=True, null=True)
    dokument = models.ForeignKey('Dokument', models.CASCADE, blank=True, null=True)
    memorabilien = models.ForeignKey('Memorabilien', models.CASCADE, blank=True, null=True)
    technik = models.ForeignKey('Technik', models.CASCADE, blank=True, null=True)
    video = models.ForeignKey('Video', models.CASCADE, blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = 'Bestand'
        verbose_name_plural = 'Bestände'
        ordering = ['pk']

    def __str__(self):
        return str(self.lagerort)

    def bestand_objekt(self):
        # TODO: WIP create a template just for bestand changeform so we can display the object in question as a link
        # art = self.bestand_art(as_field=True)
        objekt = art.value_from_object(self)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        # TODO: bestand_art should get its value from the related_model.
        # Find the correct Bestand-Art
        for fld_name, _choice in self.BESTAND_CHOICES:
            if getattr(self, fld_name):
                self.bestand_art = fld_name
        super().save(force_insert, force_update, using, update_fields)


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

    name_field = 'titel'
    primary_search_fields = ['titel']
    search_fields = ['titel', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Datei'
        verbose_name_plural = 'Dateien'

    def __str__(self):
        return str(self.titel)


class Format(ComputedNameModel):
    anzahl = models.PositiveSmallIntegerField(default=1)
    catalog_nr = models.CharField('Katalog Nummer', max_length=200, blank=True)  # TODO: nr for vinyl?? http://mikiwiki.org/wiki/Nummern_auf_Schallplatten
    bemerkungen = models.TextField(blank=True)

    audio = models.ForeignKey('Audio', models.CASCADE)
    format_typ = models.ForeignKey('FormatTyp', models.PROTECT, verbose_name='Format Typ')
    format_size = models.ForeignKey(
        'FormatSize', models.SET_NULL, verbose_name='Format Größe',
        help_text='LP, 12", Mini-Disc, etc.', blank=True, null=True
    )
    # The field 'tag' is used in a stacked inline on audio.
    # blank must be True or the inline requires a tag to be submitted.
    tag = models.ManyToManyField('FormatTag', verbose_name='Tags', blank=True)

    name_composing_fields = [
        'anzahl', 'format_size__size', 'format_typ__typ',
        'tag__tag',
    ]

    class Meta(BaseModel.Meta):
        ordering = ['_name']
        verbose_name = 'Format'
        verbose_name_plural = 'Formate'

    @classmethod
    def _get_name(cls, **data):
        """
        Construct a name from the 'data' given.
        'data' is a mapping of field_path: tuple of values provided by
        MIZQuerySet.values_dict.

        Returns a name in the format:
            '{quantity (if > 1)} {format} {tags} {channel}'
        where 'format' is either format_size or format_typ.
        """
        qty = format = tags = channel = ''
        if 'anzahl' in data and data['anzahl'][0] > 1:
            qty = str(data['anzahl'][0]) + 'x'
        if 'format_size__size' in data:
            format = str(data['format_size__size'][0])
        elif 'format_typ__typ' in data:
            format = str(data['format_typ__typ'][0])
        if'tag__tag' in data:
            tags = ", " + concat_limit(sorted(data['tag__tag']))
        if 'channel' in data:
            channel = ", " + data['channel'][0]
        return qty + format + tags + channel


class FormatTag(BaseModel):
    tag = models.CharField(max_length=200)
    abk = models.CharField('Abkürzung', max_length=200, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ['tag']
        verbose_name = 'Format-Tag'
        verbose_name_plural = 'Format-Tags'

    def __str__(self):
        return str(self.tag)


class FormatSize(BaseModel):
    size = models.CharField(max_length=200)

    class Meta(BaseModel.Meta):
        ordering = ['size']
        verbose_name = 'Format-Größe'
        verbose_name_plural = 'Format-Größen'


class FormatTyp(BaseModel):
    """Art des Formats (Vinyl, DVD, Cassette, etc)."""

    typ = models.CharField(max_length=200)

    class Meta(BaseModel.Meta):
        ordering = ['typ']
        verbose_name = 'Format-Typ'
        verbose_name_plural = 'Format-Typen'


class Plattenfirma(BaseModel):
    name = models.CharField(max_length=200)

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

    name_field = 'titel'

    def __str__(self):
        return str(self.titel)

    class Meta(BaseModel.Meta):
        ordering = ['titel']


class Brochure(BaseBrochure):
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Broschüre')

    schlagwort = models.ManyToManyField('Schlagwort')

    primary_search_fields = ['titel']
    search_fields = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {
        'zusammenfassung': 'Zusammenfassung',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen'
    }

    class Meta:
        verbose_name = 'Broschüre'
        verbose_name_plural = 'Broschüren'


class Kalender(BaseBrochure):
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Programmheftes')

    spielort = models.ManyToManyField('Spielort')
    veranstaltung = models.ManyToManyField('Veranstaltung')

    primary_search_fields = ['titel']
    search_fields = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {
        'zusammenfassung': 'Zusammenfassung',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen'
    }

    class Meta:
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
    art = models.CharField('Art d. Kataloges', max_length=40, choices=ART_CHOICES, default=ART_MERCH)

    primary_search_fields = ['titel']
    search_fields = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']
    search_fields_suffixes = {
        'zusammenfassung': 'Zusammenfassung',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen'
    }

    class Meta:
        verbose_name = 'Warenkatalog'
        verbose_name_plural = 'Warenkataloge'
