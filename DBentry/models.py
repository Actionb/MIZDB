# TODO: allow searching by ISSN
# TODO: Semantik buch.buchband: Einzelbänder/Aufsätze: Teile eines Buchbandes
# TODO: help_text for checkbox widget fields do not have 'margin-left:160;padding-left:10px':
# forms.css:126 {.aligned label + div.help} overrides the usual intendation of the help_texts
# TODO: remove CF_ARGS and CF_ARGS_B
from django.core.validators import MinValueValidator
from django.db import models

import DBentry.m2m as _m2m
from DBentry.base.models import (
    BaseModel, ComputedNameModel, BaseAliasModel, AbstractJahrModel,
    AbstractURLModel
)
from DBentry.constants import CF_ARGS, CF_ARGS_B, LIST_DISPLAY_MAX_LEN
from DBentry.fields import (
    ISSNField, ISBNField, EANField, YearField, PartialDate, PartialDateField
)
from DBentry.managers import AusgabeQuerySet, HumanNameQuerySet, PeopleQuerySet
from DBentry.utils import concat_limit


class person(ComputedNameModel):
    vorname = models.CharField(**CF_ARGS_B)
    nachname = models.CharField(**CF_ARGS)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Person')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    orte = models.ManyToManyField('ort', blank=True)

    name_composing_fields = ['vorname', 'nachname']
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


class musiker(BaseModel):
    kuenstler_name = models.CharField('Künstlername', **CF_ARGS)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Musikers')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    person = models.ForeignKey(person, models.SET_NULL, null=True, blank=True)

    genre = models.ManyToManyField('genre', through=_m2m.m2m_musiker_genre)
    instrument = models.ManyToManyField('instrument', through=_m2m.m2m_musiker_instrument)
    orte = models.ManyToManyField('ort', blank=True)

    create_field = 'kuenstler_name'
    name_field = 'kuenstler_name'
    objects = HumanNameQuerySet.as_manager()
    primary_search_fields = []
    search_fields = [
        'kuenstler_name', 'person__vorname', 'person__nachname',
        'musiker_alias__alias', 'beschreibung'
    ]
    search_fields_suffixes = {
        'person__vorname': 'Vorname',
        'person__nachname': 'Nachname',
        'musiker_alias__alias': 'Alias'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Musiker'
        verbose_name_plural = 'Musiker'
        ordering = ['kuenstler_name', 'person']
class musiker_alias(BaseAliasModel):
    parent = models.ForeignKey('musiker', models.CASCADE)


class genre(BaseModel):
    genre = models.CharField('Genre', max_length=100, unique=True)

    ober = models.ForeignKey(  # TODO: remove this field
        'self', models.SET_NULL, related_name='sub_genres', verbose_name='Oberbegriff',
        null=True, blank=True,
    )

    create_field = 'genre'
    name_field = 'genre'
    primary_search_fields = ['genre']
    search_fields = ['genre', 'ober__genre', 'sub_genres__genre', 'genre_alias__alias']
    search_fields_suffixes = {
        'ober__genre': 'Subgenre',
        'sub_genres__genre': 'Oberbegriff',
        'genre_alias__alias': 'Alias'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['genre']
class genre_alias(BaseAliasModel):
    parent = models.ForeignKey('genre', models.CASCADE)


class band(BaseModel):
    band_name = models.CharField('Bandname', **CF_ARGS)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Band')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('genre', through=_m2m.m2m_band_genre)
    musiker = models.ManyToManyField('musiker', through=_m2m.m2m_band_musiker)
    orte = models.ManyToManyField('ort', blank=True)

    create_field = 'band_name'
    name_field = 'band_name'
    primary_search_fields = ['band_name', 'band_alias__alias']
    search_fields = [
        'band_name', 'band_alias__alias', 'musiker__kuenstler_name',
        'musiker__musiker_alias__alias', 'beschreibung'
    ]
    search_fields_suffixes = {
        'band_alias__alias': 'Band-Alias',
        'musiker__kuenstler_name': 'Band-Mitglied',
        'musiker__musiker_alias__alias': 'Mitglied-Alias',
        'beschreibung': 'Beschreibung'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'
        ordering = ['band_name']
class band_alias(BaseAliasModel):
    parent = models.ForeignKey('band', models.CASCADE)


class autor(ComputedNameModel):
    kuerzel = models.CharField('Kürzel', **CF_ARGS_B)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Autors')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    person = models.ForeignKey('person', models.SET_NULL, null=True, blank=True)

    magazin = models.ManyToManyField('magazin', blank=True, through=_m2m.m2m_autor_magazin)

    name_composing_fields = ['person___name', 'kuerzel']
    objects = PeopleQuerySet.as_manager()
    primary_search_fields = []
    search_fields = ['kuerzel', 'person___name', 'beschreibung']
    search_fields_suffixes = {'beschreibung': 'Beschreibung'}

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
            person_default = person._name_default % {
                'verbose_name': person._meta.verbose_name
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


class ausgabe(ComputedNameModel):
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
        'Erscheinungsdatum', null=True, blank=True, help_text='Format: tt.mm.jjjj'
    )
    jahrgang = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Jahrgang", validators=[MinValueValidator(1)]
    )
    sonderausgabe = models.BooleanField(default=False, verbose_name='Sonderausgabe')
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Ausgabe')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    magazin = models.ForeignKey('magazin', models.PROTECT, verbose_name='Magazin')

    audio = models.ManyToManyField('audio', through=_m2m.m2m_audio_ausgabe, blank=True)

    name_composing_fields = [
        'beschreibung', 'sonderausgabe', 'e_datum', 'jahrgang',
        'magazin__ausgaben_merkmal', 'ausgabe_jahr__jahr', 'ausgabe_num__num',
        'ausgabe_lnum__lnum', 'ausgabe_monat__monat__abk'
    ]
    objects = AusgabeQuerySet.as_manager()
    primary_search_fields = ['_name']
    search_fields = [
        'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr', 'e_datum',
        'ausgabe_monat__monat__monat', 'ausgabe_monat__monat__abk', 'jahrgang',
        'beschreibung', 'bemerkungen'
    ]
    search_fields_suffixes = {
        'ausgabe_monat__monat__monat': 'Monat',
        'ausgabe_lnum__lnum': 'lfd. Num',
        'e_datum': 'E.datum',
        'ausgabe_num__num': 'Num',
        'jahrgang': 'Jahrgang',
        'ausgabe_monat__monat__abk': 'Monat Abk.',
        'ausgabe_jahr__jahr': 'Jahr',
        'beschreibung': 'Beschreibung',
        'bemerkungen': 'Bemerkungen',
    }

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
        if data.get('sonderausgabe', False) and beschreibung:
            # Special issues may be a bit... 'special' in their numerical values.
            # Just use the 'beschreibung' for such an issue.
            return beschreibung

        jahre = jahrgang = ''
        if 'jahrgang' in data:
            jahrgang = data['jahrgang'][0]
        if 'ausgabe_jahr__jahr' in data:
            # Concatenate the years given.
            # Use four digits for the first year,
            # use only the last two digits for the rest.
            jahre = [
                str(jahr)[2:] if i else str(jahr)
                for i, jahr in enumerate(sorted(data['ausgabe_jahr__jahr']))
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
        if 'ausgabe_num__num' in data:
            nums = concat_limit(
                sorted(data['ausgabe_num__num']),
                sep="/",
                z=2
            )
        if 'ausgabe_lnum__lnum' in data:
            lnums = concat_limit(
                sorted(data['ausgabe_lnum__lnum']),
                sep="/",
                z=2
            )
        if 'ausgabe_monat__monat__abk' in data:
            monat_ordering = [
                'Jan', 'Feb', 'Mrz', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep',
                'Okt', 'Nov', 'Dez'
            ]
            # Sort the month abbreviations according to the calendar.
            monate = sorted(
                data['ausgabe_monat__monat__abk'],
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


class ausgabe_jahr(BaseModel):
    jahr = YearField('Jahr')

    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)

    class Meta(BaseModel.Meta):
        verbose_name = 'Jahr'
        verbose_name_plural = 'Jahre'
        unique_together = ('jahr', 'ausgabe')
        ordering = ['jahr']


class ausgabe_num(BaseModel):
    num = models.IntegerField('Nummer')
    kuerzel = models.CharField(**CF_ARGS_B)

    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)

    class Meta(BaseModel.Meta):
        verbose_name = 'Nummer'
        verbose_name_plural = 'Ausgabennummer'
        unique_together = ('num', 'ausgabe', 'kuerzel')
        ordering = ['num']


class ausgabe_lnum(BaseModel):
    lnum = models.IntegerField('Lfd. Nummer')
    kuerzel = models.CharField(**CF_ARGS_B)

    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)

    class Meta(BaseModel.Meta):
        verbose_name = 'lfd. Nummer'
        verbose_name_plural = 'Laufende Nummer'
        unique_together = ('lnum', 'ausgabe', 'kuerzel')
        ordering = ['lnum']


class ausgabe_monat(BaseModel):
    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)
    monat = models.ForeignKey('monat', models.CASCADE)

    search_fields = ['monat__monat', 'monat__abk']

    class Meta(BaseModel.Meta):
        verbose_name = 'Ausgabe-Monat'
        verbose_name_plural = 'Ausgabe-Monate'
        unique_together = ('ausgabe', 'monat')
        ordering = ['monat']

    def __str__(self):
        return self.monat.abk


class monat(BaseModel):
    monat = models.CharField('Monat', **CF_ARGS)
    abk = models.CharField('Abk', **CF_ARGS)
    ordinal = models.PositiveSmallIntegerField(editable=False)

    class Meta(BaseModel.Meta):
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        ordering = ['ordinal']

    def __str__(self):
        return self.monat


class magazin(BaseModel):
    NUM = 'num'
    LNUM = 'lnum'
    MONAT = 'monat'
    E_DATUM = 'e_datum'
    MERKMAL_CHOICES = [
        (NUM, 'Nummer'), (LNUM, 'Lfd.Nummer'), (MONAT, 'Monat'), (E_DATUM, 'Ersch.Datum')
    ]

    magazin_name = models.CharField('Magazin', **CF_ARGS)
    magazin_url = models.URLField(verbose_name='Webpage', blank=True)
    ausgaben_merkmal = models.CharField(
        'Ausgaben Merkmal', choices=MERKMAL_CHOICES,
        help_text=('Das dominante Merkmal der Ausgaben. Diese Angabe bestimmt die Darstellung der '
            'Ausgaben in der Änderungsliste.'),
        **CF_ARGS_B
    )
    fanzine = models.BooleanField('Fanzine', default=False)
    issn = ISSNField('ISSN', blank=True,
        help_text='EAN (Barcode Nummer) Angaben erlaubt. Die ISSN wird dann daraus ermittelt.')
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Magazines')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')
    # TODO: make ort a M2M to 'ort'?
    ort = models.ForeignKey(
        'ort', models.SET_NULL, null=True, blank=True, verbose_name='Herausgabeort',
        help_text='Wenn das Magazin regional beschränkt ist, kann die Region hier angegeben werden.'
    )

    genre = models.ManyToManyField('genre', blank=True, through=_m2m.m2m_magazin_genre)
    verlag = models.ManyToManyField('verlag', through=_m2m.m2m_magazin_verlag)
    herausgeber = models.ManyToManyField('Herausgeber', through=_m2m.m2m_magazin_herausgeber)

    create_field = 'magazin_name'
    name_field = 'magazin_name'
    search_fields = ['magazin_name', 'beschreibung', 'issn']
    search_fields_suffixes = {'beschreibung': 'Beschreibung', 'issn': 'ISSN'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Magazin'
        verbose_name_plural = 'Magazine'
        ordering = ['magazin_name']

    def __str__(self):
        return str(self.magazin_name)


class verlag(BaseModel):
    verlag_name = models.CharField('Verlag', **CF_ARGS)

    sitz = models.ForeignKey('ort', models.SET_NULL, null=True, blank=True)

    create_field = 'verlag_name'
    name_field = 'verlag_name'
    search_fields = [
        'verlag_name', 'sitz___name', 'sitz__land__land_name',
        'sitz__bland__bland_name'
    ]

    class Meta(BaseModel.Meta):
        verbose_name = 'Verlag'
        verbose_name_plural = 'Verlage'
        ordering = ['verlag_name', 'sitz']


# TODO: clean up the data of models: ort/land/bland
class ort(ComputedNameModel):
    stadt = models.CharField(**CF_ARGS_B)

    bland = models.ForeignKey(
        'bundesland', models.SET_NULL, verbose_name='Bundesland', null=True, blank=True
    )
    land = models.ForeignKey('land', models.PROTECT, verbose_name='Land')

    name_composing_fields = [
        'stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code'
    ]
    primary_search_fields = []
    search_fields = ['stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code']
    search_fields_suffixes = {
        'land__code': 'Land-Code',
        'bland__code': 'Bundesland-Code',
        'bland__bland_name': 'Bundesland',
        'land_name': 'Land'
    }

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


class bundesland(BaseModel):
    bland_name = models.CharField('Bundesland', **CF_ARGS)
    code = models.CharField(max_length=4, unique=False)

    land = models.ForeignKey('land', models.PROTECT, verbose_name='Land')

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


class land(BaseModel):
    land_name = models.CharField('Land', max_length=100, unique=True)
    code = models.CharField(max_length=4, unique=True)

    name_field = 'land_name'
    primary_search_fields = ['land_name', 'code']
    search_fields = ['land_name', 'code', 'land_alias__alias']
    search_fields_suffixes = {
        'code': 'Land-Code',
        'land_alias__alias': 'Land-Alias',
    }

    def __str__(self):
        return "{} {}".format(self.land_name, self.code).strip()

    class Meta(BaseModel.Meta):
        verbose_name = 'Land'
        verbose_name_plural = 'Länder'
        ordering = ['land_name']
class land_alias(BaseAliasModel):
    parent = models.ForeignKey('land', models.CASCADE)

# TODO: make schlagwort 'view-pnly' in admin (meta.default_permissions)
class schlagwort(BaseModel):
    schlagwort = models.CharField(max_length=100, unique=True)

    ober = models.ForeignKey(  # TODO: remove this field
        'self', models.SET_NULL, related_name='unterbegriffe',
        verbose_name='Oberbegriff', null=True, blank=True
    )

    create_field = 'schlagwort'
    name_field = 'schlagwort'
    primary_search_fields = []
    search_fields = [
        'schlagwort', 'unterbegriffe__schlagwort', 'ober__schlagwort',
        'schlagwort_alias__alias'
    ]
    search_fields_suffixes = {
        'unterbegriffe__schlagwort': 'Oberbegriff',
        'ober__schlagwort': 'Unterbegriff',
        'schlagwort_alias__alias': 'Alias'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Schlagwort'
        verbose_name_plural = 'Schlagwörter'
        ordering = ['schlagwort']
class schlagwort_alias(BaseAliasModel):
    parent = models.ForeignKey('schlagwort', models.CASCADE)


class artikel(BaseModel):
    F = 'f'
    FF = 'ff'
    SU_CHOICES = [(F, 'f'), (FF, 'ff')]

    schlagzeile = models.CharField(**CF_ARGS)
    seite = models.PositiveSmallIntegerField(verbose_name="Seite")
    seitenumfang = models.CharField(
        max_length=3, blank=True, choices=SU_CHOICES, default='',
        help_text='Zwei Seiten: f; mehr als zwei Seiten: ff.'
    )
    zusammenfassung = models.TextField(blank=True)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Artikels')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    ausgabe = models.ForeignKey('ausgabe', models.PROTECT)

    genre = models.ManyToManyField('genre', through=_m2m.m2m_artikel_genre, verbose_name='Genre')
    schlagwort = models.ManyToManyField(
        'schlagwort', through=_m2m.m2m_artikel_schlagwort, verbose_name='Schlagwort'
    )
    person = models.ManyToManyField('person', through=_m2m.m2m_artikel_person)
    autor = models.ManyToManyField('autor', through=_m2m.m2m_artikel_autor)
    band = models.ManyToManyField('band', through=_m2m.m2m_artikel_band)
    musiker = models.ManyToManyField('musiker', through=_m2m.m2m_artikel_musiker)
    ort = models.ManyToManyField('ort', through=_m2m.m2m_artikel_ort)
    spielort = models.ManyToManyField('spielort', through=_m2m.m2m_artikel_spielort)
    veranstaltung = models.ManyToManyField('veranstaltung', through=_m2m.m2m_artikel_veranstaltung)

    name_field = 'schlagzeile'
    primary_search_fields = ['schlagzeile']
    search_fields = ['schlagzeile', 'zusammenfassung', 'beschreibung']
    search_fields_suffixes = {
        'zusammenfassung': 'Zusammenfassung',
        'beschreibung': 'Beschreibung'
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Artikel'
        verbose_name_plural = 'Artikel'
        ordering = ['seite', 'ausgabe', 'pk']

    def __str__(self):
        if self.schlagzeile:
            return str(self.schlagzeile)
        elif self.zusammenfassung:
            return str(self.zusammenfassung)
        else:
            return 'Keine Schlagzeile gegeben!'


class buch(BaseModel):
    # TODO: übersetzer feld
    titel = models.CharField(**CF_ARGS)
    titel_orig = models.CharField('Titel (Original)', **CF_ARGS_B)
    seitenumfang = models.PositiveSmallIntegerField(blank=True, null=True)  # TODO: Semantik: Seitenanzahl?
    jahr = YearField('Jahr', null=True, blank=True)
    jahr_orig = YearField('Jahr (Original)', null=True, blank=True)
    auflage = models.CharField(**CF_ARGS_B)
    EAN = EANField(blank=True)
    ISBN = ISBNField(blank=True)
    is_buchband = models.BooleanField(
        default=False, verbose_name='Ist Sammelband',
        help_text='Dieses Buch ist ein Sammelband bestehend aus Aufsätzen.'
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Buches')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    schriftenreihe = models.ForeignKey('schriftenreihe', models.SET_NULL, null=True, blank=True)
    buchband = models.ForeignKey(
        'self', models.PROTECT, null=True, blank=True, limit_choices_to={'is_buchband': True},
        related_name='buch_set', help_text='Der Sammelband, der diesen Aufsatz enthält.',
        verbose_name='Sammelband',
    )
    verlag = models.ForeignKey('verlag', models.SET_NULL, null=True, blank=True)
    sprache = models.CharField(max_length=200, blank=True)

    herausgeber = models.ManyToManyField('Herausgeber')
    autor = models.ManyToManyField('autor')
    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')

    name_field = 'titel'
    primary_search_fields = []
    search_fields = ['titel', 'beschreibung', 'ISBN', 'EAN']
    search_fields_suffixes = {
        'beschreibung': 'Beschreibung',
        'ISBN': 'ISBN',
        'EAN': 'EAN',
    }

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

    class Meta(BaseModel.Meta):
        ordering = ['herausgeber']
        verbose_name = 'Herausgeber'
        verbose_name_plural = 'Herausgeber'


class instrument(BaseModel):
    instrument = models.CharField(unique=True, **CF_ARGS)
    kuerzel = models.CharField(verbose_name='Kürzel', **CF_ARGS)

    name_field = 'instrument'
    primary_search_fields = ['instrument']
    search_fields = ['instrument', 'instrument_alias__alias', 'kuerzel']
    search_fields_suffixes = {
        'instrument_alias__alias': 'Alias',
        'kuerzel': 'Kürzel'
    }

    class Meta(BaseModel.Meta):
        ordering = ['instrument', 'kuerzel']
        verbose_name = 'Instrument'
        verbose_name_plural = 'Instrumente'

    def __str__(self):
        if self.kuerzel:
            return "{} ({})".format(str(self.instrument), str(self.kuerzel))
        return str(self.instrument)
class instrument_alias(BaseAliasModel):
    parent = models.ForeignKey('instrument', models.CASCADE)


class audio(BaseModel):
    titel = models.CharField(**CF_ARGS)
    tracks = models.PositiveIntegerField(verbose_name='Anz. Tracks', blank=True, null=True)
    laufzeit = models.DurationField(blank=True, null=True, help_text='Format: hh:mm:ss')
    e_jahr = YearField('Erscheinungsjahr', blank=True, null=True)
    quelle = models.CharField(help_text='Broadcast, Live, etc.', **CF_ARGS_B)  # TODO: NICHTSSAGEND
    catalog_nr = models.CharField(verbose_name='Katalog Nummer', **CF_ARGS_B)  # TODO: NICHTSSAGEND WARNING: field missing in admin
    release_id = models.PositiveIntegerField(blank=True, null=True, verbose_name="Release ID (discogs)")
    discogs_url = models.URLField(verbose_name="Link discogs.com", blank=True,
        help_text="Adresse zur discogs.com Seite dieses Objektes.")
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Mediums')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    plattenfirma = models.ManyToManyField('plattenfirma', through=_m2m.m2m_audio_plattenfirma)
    band = models.ManyToManyField('band', through=_m2m.m2m_audio_band)
    genre = models.ManyToManyField('genre', through=_m2m.m2m_audio_genre)
    musiker = models.ManyToManyField('musiker', through=_m2m.m2m_audio_musiker)
    person = models.ManyToManyField('person', through=_m2m.m2m_audio_person)
    schlagwort = models.ManyToManyField('schlagwort', through=_m2m.m2m_audio_schlagwort)
    spielort = models.ManyToManyField('spielort', through=_m2m.m2m_audio_spielort)
    veranstaltung = models.ManyToManyField('veranstaltung', through=_m2m.m2m_audio_veranstaltung)
    ort = models.ManyToManyField('ort', through=_m2m.m2m_audio_ort)

    name_field = 'titel'
    primary_search_fields = []
    search_fields = ['titel', 'beschreibung']
    search_fields_suffixes = {'beschreibung': 'Beschreibung'}

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Audio Material'
        verbose_name_plural = 'Audio Materialien'
        permissions = [
            ('alter_bestand_audio', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]

    def __str__(self):
        return str(self.titel)


class bildmaterial(BaseModel):
    titel = models.CharField(**CF_ARGS)
    signatur = models.CharField(unique=True, null=True, **CF_ARGS_B)  # TODO: help_text: frag Birgitt, was genau das ist 
    size = models.CharField(**CF_ARGS_B, verbose_name='Größe')
    datum = PartialDateField()  # TODO: add help_text to make clear this isn't the "entry" date
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Bildmaterials')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    reihe = models.ForeignKey(
        'Bildreihe', models.PROTECT, blank=True, null=True, verbose_name='Bildreihe')

    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')

    name_field = 'titel'
    primary_search_fields = ['titel', 'signatur']
    search_fields = ['titel', 'signatur', 'beschreibung']
    search_fields_suffixes = {
        'signatur': 'Signatur',
        'beschreibung': 'Beschreibung',
    }

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Bild Material'
        verbose_name_plural = 'Bild Materialien'
        permissions = [
            ('alter_bestand_bildmaterial', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class Bildreihe(BaseModel):
    name = models.CharField(**CF_ARGS)

    create_field = 'name'
    name_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Bildreihe'
        verbose_name_plural = 'Bildreihen'


class schriftenreihe(BaseModel):
    name = models.CharField(**CF_ARGS)

    create_field = 'name'
    name_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Schriftenreihe'
        verbose_name_plural = 'Schriftenreihen'


class dokument(BaseModel):
    titel = models.CharField(**CF_ARGS)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Dokumentes')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')

    name_field = 'titel'
    primary_search_fields = []
    search_fields = ['titel', 'beschreibung']
    search_fields_suffixes = {'beschreibung': 'Beschreibung'}

    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Dokument'
        verbose_name_plural = 'Dokumente'
        permissions = [
            ('alter_bestand_dokument', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class memorabilien(BaseModel):
    titel = models.CharField(**CF_ARGS)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Memorabiliums')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')

    name_field = 'titel'
    primary_search_fields = []
    search_fields = ['titel', 'beschreibung']
    search_fields_suffixes = {'beschreibung': 'Beschreibung'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Memorabilia'
        verbose_name_plural = 'Memorabilien'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_memorabilien', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class spielort(BaseModel):
    name = models.CharField(**CF_ARGS)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Spielortes')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    ort = models.ForeignKey('ort', models.PROTECT)

    name_field = 'name'
    primary_search_fields = ['name']
    search_fields = ['name', 'spielort_alias__alias', 'ort___name', 'beschreibung']
    search_fields_suffixes = {
        'spielort_alias__alias': 'Alias',
        'ort___name': 'Ort',
        'beschreibung': 'Beschreibung',
    }

    class Meta(BaseModel.Meta):
        verbose_name = 'Spielort'
        verbose_name_plural = 'Spielorte'
        ordering = ['name']
class spielort_alias(BaseAliasModel):
    parent = models.ForeignKey('spielort', models.CASCADE)


class technik(BaseModel):
    titel = models.CharField(**CF_ARGS)
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Technik')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')

    name_field = 'titel'
    primary_search_fields = []
    search_fields = ['titel', 'beschreibung']
    search_fields_suffixes = {'beschreibung': 'Beschreibung'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Technik'
        verbose_name_plural = 'Technik'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_technik', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class veranstaltung(BaseModel):
    name = models.CharField(**CF_ARGS)
    datum = PartialDateField(blank=False)

    spielort = models.ForeignKey('spielort', models.PROTECT)
    reihe = models.ForeignKey('Veranstaltungsreihe', models.PROTECT, blank=True, null=True)

    beschreibung = models.TextField(blank=True)
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    genre = models.ManyToManyField('genre')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    schlagwort = models.ManyToManyField('schlagwort')
    musiker = models.ManyToManyField('musiker')

    name_field = 'name'
    primary_search_fields = ['name']
    search_fields = ['name', 'veranstaltung_alias__alias', 'beschreibung']
    search_fields_suffixes = {
        'veranstaltung_alias__alias': 'Alias',
        'beschreibung': 'Beschreibung',
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
class veranstaltung_alias(BaseAliasModel):
    parent = models.ForeignKey('veranstaltung', models.CASCADE)


class Veranstaltungsreihe(BaseModel):
    name = models.CharField(**CF_ARGS)

    create_field = 'name'
    name_field = 'name'
    search_fields = ['name']

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Veranstaltungsreihe'
        verbose_name_plural = 'Veranstaltungsreihen'


class video(BaseModel):
    titel = models.CharField(**CF_ARGS)
    tracks = models.IntegerField()  # TODO: PositiveSmallIntegerField!
    laufzeit = models.DurationField(blank=True, null=True, help_text='Format: hh:mm:ss')
    festplatte = models.CharField(**CF_ARGS_B)  # TODO: "Speicherort"?? shouldnt this be a relation to Datei then?
    quelle = models.CharField(**CF_ARGS_B)  # TODO: same as audio.quelle?
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Mediums')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    band = models.ManyToManyField('band')
    genre = models.ManyToManyField('genre')
    musiker = models.ManyToManyField('musiker', through=_m2m.m2m_video_musiker)
    person = models.ManyToManyField('person')
    schlagwort = models.ManyToManyField('schlagwort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')

    name_field = 'titel'
    primary_search_fields = []
    search_fields = ['titel', 'beschreibung']
    search_fields_suffixes = {'beschreibung': 'Beschreibung'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Video Material'
        verbose_name_plural = 'Video Materialien'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_video', 'Aktion: Bestand/Dublette hinzufügen.'),
        ]


class provenienz(BaseModel):
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
        'Art der Provenienz', max_length=100, choices=TYP_CHOICES, default=TYP_CHOICES[0][0]
    )

    geber = models.ForeignKey('geber', models.PROTECT)

    search_fields = ['geber__name']

    class Meta(BaseModel.Meta):
        ordering = ['geber', 'typ']
        verbose_name = 'Provenienz'
        verbose_name_plural = 'Provenienzen'

    def __str__(self):
        return "{0} ({1})".format(str(self.geber.name), str(self.typ))


class geber(BaseModel):
    # TODO: merge with person?
    name = models.CharField(default='unbekannt', **CF_ARGS)

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Geber'
        verbose_name_plural = 'Geber'


class lagerort(ComputedNameModel):
    ort = models.CharField(**CF_ARGS)
    raum = models.CharField(**CF_ARGS_B)
    regal = models.CharField(**CF_ARGS_B)
    fach = models.CharField(**CF_ARGS_B)
    ordner = models.CharField(**CF_ARGS_B)

    name_composing_fields = ['ort', 'raum', 'regal', 'fach']

    class Meta(BaseModel.Meta):
        verbose_name = 'Lagerort'
        verbose_name_plural = 'Lagerorte'
        ordering = ['ort']

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


class bestand(BaseModel):
    BESTAND_CHOICES = [
        ('audio', 'Audio'), ('ausgabe', 'Ausgabe'), ('bildmaterial', 'Bildmaterial'),
        ('buch', 'Buch'), ('dokument', 'Dokument'), ('memorabilien', 'Memorabilien'),
        ('technik', 'Technik'), ('video', 'Video'),
    ]
    signatur = models.AutoField(primary_key=True)
    bestand_art = models.CharField(
        'Bestand-Art', max_length=20, choices=BESTAND_CHOICES, blank=False, default='ausgabe'
    )

    lagerort = models.ForeignKey('lagerort', models.PROTECT)
    provenienz = models.ForeignKey('provenienz', models.SET_NULL, blank=True, null=True)

    audio = models.ForeignKey('audio', models.CASCADE, blank=True, null=True)
    ausgabe = models.ForeignKey('ausgabe', models.CASCADE, blank=True, null=True)
    bildmaterial = models.ForeignKey('bildmaterial', models.CASCADE, blank=True, null=True)
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, blank=True, null=True)
    buch = models.ForeignKey('buch', models.CASCADE, blank=True, null=True)
    dokument = models.ForeignKey('dokument', models.CASCADE, blank=True, null=True)
    memorabilien = models.ForeignKey('memorabilien', models.CASCADE, blank=True, null=True)
    technik = models.ForeignKey('technik', models.CASCADE, blank=True, null=True)
    video = models.ForeignKey('video', models.CASCADE, blank=True, null=True)

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
        super(bestand, self).save(force_insert, force_update, using, update_fields)


class datei(BaseModel):
    MEDIA_AUDIO = 'audio'
    MEDIA_BILD = 'bild'
    MEDIA_SONSTIGE = 'sonstige'
    MEDIA_TEXT = 'text'
    MEDIA_VIDEO = 'video'
    MEDIA_TYP_CHOICES = [
        (MEDIA_AUDIO, 'Audio'), (MEDIA_VIDEO, 'Video'), (MEDIA_BILD, 'Bild'),
        (MEDIA_TEXT, 'Text'), (MEDIA_SONSTIGE, 'Sonstige')
    ]

    titel = models.CharField(**CF_ARGS)
    media_typ = models.CharField(
        choices=MEDIA_TYP_CHOICES, verbose_name='Media Typ', default='audio', **CF_ARGS
    )
    datei_media = models.FileField(  # Datei Media Server
        verbose_name='Datei', blank=True, null=True, editable=False,
        help_text="Datei auf Datenbank-Server hoch- bzw herunterladen."
    )
    datei_pfad = models.CharField(
        verbose_name='Datei-Pfad',
        help_text="Pfad (inklusive Datei-Namen und Endung) zur Datei im gemeinsamen Ordner.",
        **CF_ARGS_B
    )
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Datei')
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    provenienz = models.ForeignKey('provenienz', models.SET_NULL, blank=True, null=True)

    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker', through=_m2m.m2m_datei_musiker)
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')

    name_field = 'titel'
    primary_search_fields = []
    search_fields = ['titel', 'beschreibung']
    search_fields_suffixes = {'beschreibung': 'Beschreibung'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Datei'
        verbose_name_plural = 'Dateien'

    def __str__(self):
        return str(self.titel)


class Format(ComputedNameModel):
    anzahl = models.PositiveSmallIntegerField(default=1)
    catalog_nr = models.CharField(verbose_name="Katalog Nummer", **CF_ARGS_B)  # TODO: nr for vinyl??
    bemerkungen = models.TextField(blank=True)

    audio = models.ForeignKey('audio', models.CASCADE)
    format_typ = models.ForeignKey('FormatTyp', models.PROTECT, verbose_name='Format Typ')
    format_size = models.ForeignKey(
        'FormatSize', models.SET_NULL, verbose_name='Format Größe',
        help_text='LP, 12", Mini-Disc, etc.', blank=True, null=True
    )

    tag = models.ManyToManyField('FormatTag', verbose_name='Tags', blank=True)

    name_composing_fields = [
        'anzahl', 'format_size__size', 'format_typ__typ',
        'tag__tag',
    ]

    class Meta(BaseModel.Meta):
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
    tag = models.CharField(**CF_ARGS)
    abk = models.CharField(verbose_name='Abkürzung', **CF_ARGS_B)

    class Meta(BaseModel.Meta):
        ordering = ['tag']
        verbose_name = 'Format-Tag'
        verbose_name_plural = 'Format-Tags'

    def __str__(self):
        return str(self.tag)


class FormatSize(BaseModel):
    size = models.CharField(**CF_ARGS)

    class Meta(BaseModel.Meta):
        ordering = ['size']
        verbose_name = 'Format-Größe'
        verbose_name_plural = 'Format-Größen'


class FormatTyp(BaseModel):
    """Art des Formats (Vinyl, DVD, Cassette, etc)."""

    typ = models.CharField(**CF_ARGS)

    class Meta(BaseModel.Meta):
        ordering = ['typ']
        verbose_name = 'Format-Typ'
        verbose_name_plural = 'Format-Typen'


class plattenfirma(BaseModel):
    name = models.CharField(**CF_ARGS)

    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Plattenfirma'
        verbose_name_plural = 'Plattenfirmen'


class BrochureYear(AbstractJahrModel):
    brochure = models.ForeignKey(
        'BaseBrochure', models.CASCADE, related_name='jahre', blank=True, null=True
    )


class BrochureURL(AbstractURLModel):
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, related_name='urls', blank=True)


class BaseBrochure(BaseModel):
    titel = models.CharField(**CF_ARGS)
    zusammenfassung = models.TextField(blank=True)
    bemerkungen = models.TextField(blank=True, help_text='Kommentare für Archiv-Mitarbeiter')

    ausgabe = models.ForeignKey(
        'ausgabe', models.SET_NULL, related_name='beilagen',
        verbose_name='Ausgabe', blank=True, null=True
    )

    genre = models.ManyToManyField('genre')

    name_field = 'titel'

    def __str__(self):
        return str(self.titel)

    class Meta(BaseModel.Meta):
        ordering = ['titel']


class Brochure(BaseBrochure):
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. der Broschüre')

    schlagwort = models.ManyToManyField('schlagwort')

    class Meta(BaseBrochure.Meta):
        verbose_name = 'Broschüre'
        verbose_name_plural = 'Broschüren'


class Kalendar(BaseBrochure):  # TODO: spelling: Kalender
    beschreibung = models.TextField(blank=True, help_text='Beschreibung bzgl. des Programmheftes')

    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')

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
    art = models.CharField('Art d. Kataloges', max_length=40, choices=ART_CHOICES, default=ART_MERCH)

    class Meta(BaseBrochure.Meta):
        verbose_name = 'Warenkatalog'
        verbose_name_plural = 'Warenkataloge'


class Favoriten(models.Model):
    user = models.OneToOneField('auth.User', models.CASCADE, editable=False)
    fav_genres = models.ManyToManyField('genre', verbose_name='Favoriten Genre', blank=True)
    fav_schl = models.ManyToManyField('schlagwort', verbose_name='Favoriten Schlagworte', blank=True)

    def __str__(self):
        return 'Favoriten von {}'.format(self.user)

    def get_favorites(self, model=None):
        rslt = {
            fld.related_model: getattr(self, fld.name).all()
            for fld in Favoriten._meta.many_to_many
        }
        if model:
            return rslt.get(model, Favoriten.objects.none())
        return rslt

    @classmethod
    def get_favorite_models(cls):
        return [fld.related_model for fld in cls._meta.many_to_many]
