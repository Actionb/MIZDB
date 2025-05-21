"""
Add and change views for the MIZDB models.

Declare a change view like this:

    @register_edit(Pizza)
    class PizzaEditView(BaseEditView):
        model = Pizza


To declare inlines for handling relations:

    @register_edit(Pizza)
    class PizzaEditView(BaseEditView):
        class ToppingsInline(Inline):
            model = Toppings

        model = Pizza
        inlines = [ToppingsInline]
"""

from django import forms
from django.urls import NoReverseMatch, reverse, reverse_lazy

from dbentry import models as _models
from dbentry.autocomplete.widgets import make_widget
from dbentry.forms import GoogleBtnWidget
from dbentry.site import forms as _forms
from dbentry.site.registry import register_edit
from dbentry.site.views.base import BaseEditView, Inline
from dbentry.utils.url import urlname


class BestandInline(Inline):
    form = _forms.BestandInlineForm
    model = _models.Bestand
    verbose_name = "Bestand"
    verbose_name_plural = "Bestände"
    fields = ["signatur", "lagerort", "provenienz", "anmerkungen"]


@register_edit(_models.Audio)
class AudioView(BaseEditView):
    class MusikerInline(Inline):
        model = _models.Audio.musiker.through
        verbose_model = _models.Musiker
        tabular = False
        changelist_fk_field = "musiker"

    class BandInline(Inline):
        model = _models.Audio.band.through
        verbose_model = _models.Band

    class SchlagwortInline(Inline):
        model = _models.Audio.schlagwort.through
        verbose_model = _models.Schlagwort

    class GenreInline(Inline):
        model = _models.Audio.genre.through
        verbose_model = _models.Genre

    class OrtInline(Inline):
        model = _models.Audio.ort.through
        verbose_model = _models.Ort

    class SpielortInline(Inline):
        model = _models.Audio.spielort.through
        verbose_model = _models.Spielort

    class VeranstaltungInline(Inline):
        model = _models.Audio.veranstaltung.through
        verbose_model = _models.Veranstaltung

    class PersonInline(Inline):
        model = _models.Audio.person.through
        verbose_model = _models.Person

    class PlattenInline(Inline):
        model = _models.Audio.plattenfirma.through
        verbose_model = _models.Plattenfirma

    class AusgabeInline(Inline):
        form = _forms.AusgabeInlineForm
        fields = ["ausgabe__magazin", "ausgabe"]
        model = _models.Ausgabe.audio.through
        verbose_model = _models.Ausgabe
        tabular = False

    model = _models.Audio
    fields = [
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
        "beschreibung",
        "bemerkungen",
    ]
    inlines = [
        MusikerInline,
        BandInline,
        SchlagwortInline,
        GenreInline,
        OrtInline,
        SpielortInline,
        VeranstaltungInline,
        PersonInline,
        PlattenInline,
        AusgabeInline,
        BestandInline,
    ]
    form = _forms.AudioForm
    offline_help_url = reverse_lazy("help", kwargs={"page_name": "audio"})


@register_edit(_models.Ausgabe)
class AusgabeView(BaseEditView):
    class NumInline(Inline):
        model = _models.AusgabeNum
        verbose_name_plural = "Ausgabennummern"

    class MonatInline(Inline):
        model = _models.AusgabeMonat
        verbose_model = _models.Monat

    class LNumInline(Inline):
        model = _models.AusgabeLnum

    class JahrInline(Inline):
        model = _models.AusgabeJahr
        verbose_name_plural = "erschienen im Jahr"

    class AudioInline(Inline):
        model = _models.Ausgabe.audio.through
        verbose_model = _models.Audio
        widgets = {
            "audio": make_widget(
                _models.Audio,
                tabular=True,
                extra_columns={"jahr": "Jahr", "medium__medium": "Medium", "kuenstler_list": "Künstler"},
                can_remove=False,
            )
        }

    class VideoInline(Inline):
        model = _models.Ausgabe.video.through
        verbose_model = _models.Video
        widgets = {
            "video": make_widget(
                _models.Video,
                tabular=True,
                extra_columns={"medium__medium": "Medium", "kuenstler_list": "Künstler"},
                can_remove=False,
            )
        }

    model = _models.Ausgabe
    fields = ["magazin", "status", "sonderausgabe", "e_datum", "jahrgang", "beschreibung", "bemerkungen"]
    inlines = [NumInline, MonatInline, LNumInline, JahrInline, AudioInline, VideoInline, BestandInline]
    widgets = {
        "sonderausgabe": forms.Select(choices=[(True, "Ja"), (False, "Nein")]),
        "e_datum": forms.DateInput(attrs={"type": "date"}),
    }
    require_confirmation = True
    confirmation_threshold = 0.8


@register_edit(_models.Autor)
class AutorView(BaseEditView):
    class URLInline(Inline):
        model = _models.AutorURL

    class MagazinInline(Inline):
        model = _models.Autor.magazin.through
        verbose_model = _models.Magazin

    model = _models.Autor
    fields = ["person", "kuerzel", "beschreibung", "bemerkungen"]
    inlines = [URLInline, MagazinInline]
    form = _forms.AutorForm
    require_confirmation = True


@register_edit(_models.Artikel)
class ArtikelView(BaseEditView):
    class AutorInline(Inline):
        model = _models.Artikel.autor.through
        verbose_model = _models.Autor

    class MusikerInline(Inline):
        model = _models.Artikel.musiker.through
        verbose_model = _models.Musiker

    class BandInline(Inline):
        model = _models.Artikel.band.through
        verbose_model = _models.Band

    class SchlagwortInline(Inline):
        model = _models.Artikel.schlagwort.through
        verbose_model = _models.Schlagwort

    class GenreInline(Inline):
        model = _models.Artikel.genre.through
        verbose_model = _models.Genre

    class OrtInline(Inline):
        model = _models.Artikel.ort.through
        verbose_model = _models.Ort

    class SpielortInline(Inline):
        model = _models.Artikel.spielort.through
        verbose_model = _models.Spielort

    class VeranstaltungInline(Inline):
        model = _models.Artikel.veranstaltung.through
        verbose_model = _models.Veranstaltung

    class PersonInline(Inline):
        model = _models.Artikel.person.through
        verbose_model = _models.Person

    model = _models.Artikel
    fields = [
        "ausgabe__magazin",
        "ausgabe",
        "schlagzeile",
        "seite",
        "seitenumfang",
        "zusammenfassung",
        "beschreibung",
        "bemerkungen",
    ]
    inlines = [
        AutorInline,
        MusikerInline,
        BandInline,
        SchlagwortInline,
        GenreInline,
        OrtInline,
        SpielortInline,
        VeranstaltungInline,
        PersonInline,
    ]
    form = _forms.ArtikelForm


@register_edit(_models.Band)
class BandView(BaseEditView):
    class URLInline(Inline):
        model = _models.BandURL

    class GenreInline(Inline):
        model = _models.Band.genre.through
        verbose_model = _models.Genre

    class AliasInline(Inline):
        model = _models.BandAlias
        verbose_name_plural = "Alias"

    class MusikerInline(Inline):
        model = _models.Band.musiker.through
        verbose_name = "Band-Mitglied"
        verbose_name_plural = "Band-Mitglieder"

    class OrtInline(Inline):
        model = _models.Band.orte.through
        verbose_name = "Ort"
        verbose_name_plural = "Assoziierte Orte"

    model = _models.Band
    inlines = [URLInline, GenreInline, AliasInline, MusikerInline, OrtInline]
    widgets = {"band_name": GoogleBtnWidget()}
    require_confirmation = True


@register_edit(_models.Plakat)
class PlakatView(BaseEditView):
    class SchlagwortInline(Inline):
        model = _models.Plakat.schlagwort.through
        verbose_model = _models.Schlagwort

    class GenreInline(Inline):
        model = _models.Plakat.genre.through
        verbose_model = _models.Genre

    class MusikerInline(Inline):
        model = _models.Plakat.musiker.through
        verbose_model = _models.Musiker

    class BandInline(Inline):
        model = _models.Plakat.band.through
        verbose_model = _models.Band

    class OrtInline(Inline):
        model = _models.Plakat.ort.through
        verbose_model = _models.Ort

    class SpielortInline(Inline):
        model = _models.Plakat.spielort.through
        verbose_model = _models.Spielort

    class VeranstaltungInline(Inline):
        model = _models.Plakat.veranstaltung.through
        verbose_model = _models.Veranstaltung

    class PersonInline(Inline):
        model = _models.Plakat.person.through
        verbose_model = _models.Person

    form = _forms.PlakatForm
    model = _models.Plakat
    fields = ["titel", "plakat_id", "size", "datum", "reihe", "beschreibung", "bemerkungen"]
    inlines = [
        SchlagwortInline,
        GenreInline,
        MusikerInline,
        BandInline,
        OrtInline,
        SpielortInline,
        VeranstaltungInline,
        PersonInline,
        BestandInline,
    ]


@register_edit(_models.Buch)
class BuchView(BaseEditView):
    class AutorInline(Inline):
        model = _models.Buch.autor.through
        verbose_model = _models.Autor

    class MusikerInline(Inline):
        model = _models.Buch.musiker.through
        verbose_model = _models.Musiker

    class BandInline(Inline):
        model = _models.Buch.band.through
        verbose_model = _models.Band

    class SchlagwortInline(Inline):
        model = _models.Buch.schlagwort.through
        verbose_model = _models.Schlagwort

    class GenreInline(Inline):
        model = _models.Buch.genre.through
        verbose_model = _models.Genre

    class OrtInline(Inline):
        model = _models.Buch.ort.through
        verbose_model = _models.Ort

    class SpielortInline(Inline):
        model = _models.Buch.spielort.through
        verbose_model = _models.Spielort

    class VeranstaltungInline(Inline):
        model = _models.Buch.veranstaltung.through
        verbose_model = _models.Veranstaltung

    class PersonInline(Inline):
        model = _models.Buch.person.through
        verbose_model = _models.Person

    class HerausgeberInline(Inline):
        model = _models.Buch.herausgeber.through
        verbose_model = _models.Herausgeber

    class VerlagInline(Inline):
        model = _models.Buch.verlag.through
        verbose_model = _models.Verlag

    template_name = "mizdb/buch_form.html"
    model = _models.Buch
    fields = [
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
        "beschreibung",
        "bemerkungen",
        "titel_orig",
        "jahr_orig",
    ]
    inlines = [
        AutorInline,
        MusikerInline,
        BandInline,
        SchlagwortInline,
        GenreInline,
        OrtInline,
        SpielortInline,
        VeranstaltungInline,
        PersonInline,
        HerausgeberInline,
        VerlagInline,
        BestandInline,
    ]
    form = _forms.BuchForm
    changelist_link_labels = {"buch": "Aufsätze"}


@register_edit(_models.Genre)
class GenreView(BaseEditView):
    class AliasInline(Inline):
        model = _models.GenreAlias
        verbose_name_plural = "Alias"

    model = _models.Genre
    inlines = [AliasInline]
    require_confirmation = True

    def get_changelist_links(self, labels=None):
        links = super().get_changelist_links(labels)
        # Add links to the Brochure models, if any.
        # Links to these models are ignored by the default implementation in
        # super() because the relation only exists on the BaseBrochure model
        # (and not the concrete child models that "inherit" the relation)
        # which does not have a changelist view and thus no URL.
        for model in (_models.Brochure, _models.Kalender, _models.Katalog):
            qs = model.objects.filter(genre=self.object)
            if c := qs.count():
                try:
                    url = reverse(urlname("changelist", model._meta))
                except NoReverseMatch:  # pragma: no cover
                    continue
                links.append((f"{url}?genre={self.object.pk}", model._meta.verbose_name_plural, c))
        return links


@register_edit(_models.Magazin)
class MagazinView(BaseEditView):
    class URLInline(Inline):
        model = _models.MagazinURL

    class GenreInline(Inline):
        model = _models.Magazin.genre.through
        verbose_model = _models.Genre

    class VerlagInline(Inline):
        model = _models.Magazin.verlag.through
        verbose_model = _models.Verlag

    class HerausgeberInline(Inline):
        model = _models.Magazin.herausgeber.through
        verbose_model = _models.Herausgeber

    class OrtInline(Inline):
        model = _models.Magazin.orte.through
        verbose_name = "Ort"
        verbose_name_plural = "Assoziierte Orte"

    model = _models.Magazin
    widgets = {"fanzine": _forms.boolean_select}
    inlines = [URLInline, GenreInline, VerlagInline, HerausgeberInline, OrtInline]
    require_confirmation = True


@register_edit(_models.Musiker)
class MusikerView(BaseEditView):
    class URLInline(Inline):
        model = _models.MusikerURL

    class GenreInline(Inline):
        model = _models.Musiker.genre.through
        verbose_model = _models.Genre

    class AliasInline(Inline):
        model = _models.MusikerAlias
        verbose_name_plural = "Alias"

    class BandInline(Inline):
        model = _models.Band.musiker.through
        verbose_name = "Band"
        verbose_name_plural = "Bands (Mitglied)"

    class OrtInline(Inline):
        model = _models.Musiker.orte.through
        verbose_name = "Ort"
        verbose_name_plural = "Assoziierte Orte"

    class InstrInline(Inline):
        model = _models.Musiker.instrument.through
        verbose_name = "Instrument"
        verbose_name_plural = "Instrumente"

    model = _models.Musiker
    fields = ["kuenstler_name", "person", "beschreibung", "bemerkungen"]
    inlines = [URLInline, GenreInline, AliasInline, BandInline, OrtInline, InstrInline]
    widgets = {"kuenstler_name": GoogleBtnWidget()}
    require_confirmation = True


@register_edit(_models.Person)
class PersonView(BaseEditView):
    class URLInline(Inline):
        model = _models.PersonURL

    class OrtInline(Inline):
        model = _models.Person.orte.through
        verbose_name = "Ort"
        verbose_name_plural = "Assoziierte Orte"

    model = _models.Person
    fields = ["vorname", "nachname", "beschreibung", "bemerkungen"]
    inlines = [URLInline, OrtInline]
    form = _forms.PersonForm
    require_confirmation = True


@register_edit(_models.Schlagwort)
class SchlagwortView(BaseEditView):
    class AliasInline(Inline):
        model = _models.SchlagwortAlias
        verbose_name_plural = "Alias"

    model = _models.Schlagwort
    inlines = [AliasInline]
    require_confirmation = True


@register_edit(_models.Spielort)
class SpielortView(BaseEditView):
    class URLInline(Inline):
        model = _models.SpielortURL

    class AliasInline(Inline):
        model = _models.SpielortAlias
        verbose_name_plural = "Alias"

    model = _models.Spielort
    fields = ["name", "ort", "beschreibung", "bemerkungen"]
    inlines = [URLInline, AliasInline]
    require_confirmation = True


@register_edit(_models.Veranstaltung)
class VeranstaltungView(BaseEditView):
    class URLInline(Inline):
        model = _models.VeranstaltungURL

    class AliasInline(Inline):
        model = _models.VeranstaltungAlias
        verbose_name_plural = "Alias"

    class MusikerInline(Inline):
        model = _models.Veranstaltung.musiker.through
        verbose_model = _models.Musiker

    class BandInline(Inline):
        model = _models.Veranstaltung.band.through
        verbose_model = _models.Band

    class SchlagwortInline(Inline):
        model = _models.Veranstaltung.schlagwort.through
        verbose_model = _models.Schlagwort

    class GenreInline(Inline):
        model = _models.Veranstaltung.genre.through
        verbose_model = _models.Genre

    class PersonInline(Inline):
        model = _models.Veranstaltung.person.through
        verbose_model = _models.Person

    model = _models.Veranstaltung
    inlines = [URLInline, AliasInline, MusikerInline, BandInline, SchlagwortInline, GenreInline, PersonInline]
    require_confirmation = True


@register_edit(_models.Verlag)
class VerlagView(BaseEditView):
    model = _models.Verlag


@register_edit(_models.Video)
class VideoView(BaseEditView):
    class MusikerInline(Inline):
        model = _models.Video.musiker.through
        verbose_model = _models.Musiker
        tabular = False
        changelist_fk_field = "musiker"

    class BandInline(Inline):
        model = _models.Video.band.through
        verbose_model = _models.Band

    class SchlagwortInline(Inline):
        model = _models.Video.schlagwort.through
        verbose_model = _models.Schlagwort

    class GenreInline(Inline):
        model = _models.Video.genre.through
        verbose_model = _models.Genre

    class OrtInline(Inline):
        model = _models.Video.ort.through
        verbose_model = _models.Ort

    class SpielortInline(Inline):
        model = _models.Video.spielort.through
        verbose_model = _models.Spielort

    class VeranstaltungInline(Inline):
        model = _models.Video.veranstaltung.through
        verbose_model = _models.Veranstaltung

    class PersonInline(Inline):
        model = _models.Video.person.through
        verbose_model = _models.Person

    class AusgabeInline(Inline):
        form = _forms.AusgabeInlineForm
        fields = ["ausgabe__magazin", "ausgabe"]
        model = _models.Ausgabe.video.through
        verbose_model = _models.Ausgabe
        tabular = False

    model = _models.Video
    fields = [
        "titel",
        "laufzeit",
        "jahr",
        "original",
        "quelle",
        "medium",
        "medium_qty",
        "beschreibung",
        "bemerkungen",
        "release_id",
        "discogs_url",
    ]
    inlines = [
        MusikerInline,
        BandInline,
        SchlagwortInline,
        GenreInline,
        OrtInline,
        SpielortInline,
        VeranstaltungInline,
        PersonInline,
        AusgabeInline,
        BestandInline,
    ]
    form = _forms.VideoForm
    offline_help_url = reverse_lazy("help", kwargs={"page_name": "video"})


@register_edit(_models.Ort)
class OrtView(BaseEditView):
    model = _models.Ort
    fields = ["stadt", "land", "bland"]
    require_confirmation = True


@register_edit(_models.Bestand)
class BestandView(BaseEditView):
    model = _models.Bestand
    require_confirmation = True

    def get(self, request, *args, **kwargs):
        return self.view_only(request)


@register_edit(_models.Instrument)
class InstrumentView(BaseEditView):
    model = _models.Instrument
    require_confirmation = True


@register_edit(_models.Herausgeber)
class HerausgeberView(BaseEditView):
    model = _models.Herausgeber
    require_confirmation = True


@register_edit(_models.Brochure)
class BrochureView(BaseEditView):
    class URLInline(Inline):
        model = _models.BrochureURL

    class JahrInline(Inline):
        model = _models.BrochureYear

    class GenreInline(Inline):
        model = _models.BaseBrochure.genre.through
        verbose_model = _models.Genre

    class SchlagwortInline(Inline):
        model = _models.Brochure.schlagwort.through
        verbose_model = _models.Schlagwort

    template_name = "mizdb/brochure_form.html"
    model = _models.Brochure
    inlines = [URLInline, JahrInline, GenreInline, SchlagwortInline, BestandInline]
    form = _forms.BrochureForm
    fields = [
        "titel",
        "zusammenfassung",
        "ausgabe__magazin",
        "ausgabe",
        "beschreibung",
        "bemerkungen",
    ]


@register_edit(_models.Katalog)
class KatalogView(BaseEditView):
    class URLInline(Inline):
        model = _models.BrochureURL

    class JahrInline(Inline):
        model = _models.BrochureYear

    class GenreInline(Inline):
        model = _models.BaseBrochure.genre.through
        verbose_model = _models.Genre

    template_name = "mizdb/brochure_form.html"
    model = _models.Katalog
    inlines = [URLInline, JahrInline, GenreInline, BestandInline]
    form = _forms.BrochureForm
    fields = [
        "titel",
        "art",
        "zusammenfassung",
        "ausgabe__magazin",
        "ausgabe",
        "beschreibung",
        "bemerkungen",
    ]


@register_edit(_models.Kalender)
class KalenderView(BaseEditView):
    class URLInline(Inline):
        model = _models.BrochureURL

    class JahrInline(Inline):
        model = _models.BrochureYear

    class GenreInline(Inline):
        model = _models.BaseBrochure.genre.through
        verbose_model = _models.Genre

    class SpielortInline(Inline):
        model = _models.Kalender.spielort.through
        verbose_model = _models.Spielort

    class VeranstaltungInline(Inline):
        model = _models.Kalender.veranstaltung.through
        verbose_model = _models.Veranstaltung

    template_name = "mizdb/brochure_form.html"
    model = _models.Kalender
    inlines = [URLInline, JahrInline, GenreInline, SpielortInline, VeranstaltungInline, BestandInline]
    form = _forms.BrochureForm
    fields = [
        "titel",
        "zusammenfassung",
        "ausgabe__magazin",
        "ausgabe",
        "beschreibung",
        "bemerkungen",
    ]


@register_edit(_models.Foto)
class FotoView(BaseEditView):
    class SchlagwortInline(Inline):
        model = _models.Foto.schlagwort.through
        verbose_model = _models.Schlagwort

    class GenreInline(Inline):
        model = _models.Foto.genre.through
        verbose_model = _models.Genre

    class MusikerInline(Inline):
        model = _models.Foto.musiker.through
        verbose_model = _models.Musiker

    class BandInline(Inline):
        model = _models.Foto.band.through
        verbose_model = _models.Band

    class OrtInline(Inline):
        model = _models.Foto.ort.through
        verbose_model = _models.Ort

    class SpielortInline(Inline):
        model = _models.Foto.spielort.through
        verbose_model = _models.Spielort

    class VeranstaltungInline(Inline):
        model = _models.Foto.veranstaltung.through
        verbose_model = _models.Veranstaltung

    class PersonInline(Inline):
        model = _models.Foto.person.through
        verbose_model = _models.Person

    form = _forms.FotoForm
    model = _models.Foto
    fields = [
        "titel",
        "foto_id",
        "size",
        "typ",
        "farbe",
        "datum",
        "reihe",
        "owner",
        "beschreibung",
        "bemerkungen",
    ]
    inlines = [
        SchlagwortInline,
        GenreInline,
        MusikerInline,
        BandInline,
        OrtInline,
        SpielortInline,
        VeranstaltungInline,
        PersonInline,
        BestandInline,
    ]
    widgets = {"farbe": _forms.boolean_select}


@register_edit(_models.Plattenfirma)
class PlattenfirmaView(BaseEditView):
    model = _models.Plattenfirma
    require_confirmation = True


@register_edit(_models.Lagerort)
class LagerortView(BaseEditView):
    model = _models.Lagerort
    require_confirmation = True


@register_edit(_models.Geber)
class GeberView(BaseEditView):
    model = _models.Geber
    require_confirmation = True


@register_edit(_models.Provenienz)
class ProvenienzView(BaseEditView):
    model = _models.Provenienz
    require_confirmation = True


@register_edit(_models.Schriftenreihe)
class SchriftenreiheView(BaseEditView):
    model = _models.Schriftenreihe
    require_confirmation = True


@register_edit(_models.Bildreihe)
class BildreiheView(BaseEditView):
    model = _models.Bildreihe
    require_confirmation = True


@register_edit(_models.Veranstaltungsreihe)
class VeranstaltungsreiheView(BaseEditView):
    model = _models.Veranstaltungsreihe
    require_confirmation = True


@register_edit(_models.VideoMedium)
class VideoMediumView(BaseEditView):
    model = _models.VideoMedium
    require_confirmation = True


@register_edit(_models.AudioMedium)
class AudioMediumView(BaseEditView):
    model = _models.AudioMedium
    require_confirmation = True
