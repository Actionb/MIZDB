from django import forms
from django.db import models

from dbentry import forms as base_forms
from dbentry import models as _models
from dbentry.autocomplete.widgets import make_widget
from dbentry.base.forms import DiscogsFormMixin, InlineFormBase, MinMaxRequiredFormMixin
from dbentry.forms import AusgabeMagazinFieldForm
from dbentry.search.forms import SearchForm
from dbentry.site.widgets import MIZURLInput

boolean_select = forms.Select(choices=[(True, "Ja"), (False, "Nein")])
null_boolean_select = forms.Select(choices=[(None, "---------"), (True, "Ja"), (False, "Nein")])


def _formfield_for_db_field(db_field, is_inline=False, **kwargs):
    """
    Create formfields for the given db_field.

    Unless specified, this function will set the widgets for relation and URL
    fields.
    """
    if isinstance(db_field, models.ManyToManyField):
        kwargs["required"] = False
        if "widget" not in kwargs:
            kwargs["widget"] = make_widget(db_field.related_model, multiple=True)
    if isinstance(db_field, models.ForeignKey):
        kwargs["empty_label"] = None
        if "widget" not in kwargs:
            # Never allow removal of selected items for single select widgets
            # in inline forms.
            can_remove = False if is_inline else db_field.blank
            kwargs["widget"] = make_widget(db_field.related_model, can_remove=can_remove)
    if isinstance(db_field, models.URLField):
        if "widget" not in kwargs:
            kwargs["widget"] = MIZURLInput
    return db_field.formfield(**kwargs)


def edit_formfield_callback(db_field, **kwargs):
    """Create formfields for edit forms."""
    return _formfield_for_db_field(db_field, is_inline=False, **kwargs)


def inline_formfield_callback(db_field, **kwargs):
    """Create formfields for inline formset forms."""
    return _formfield_for_db_field(db_field, is_inline=True, **kwargs)


class MIZEditForm(forms.ModelForm):
    """Base class for edit forms."""

    class Meta:
        formfield_callback = edit_formfield_callback


class ArtikelForm(AusgabeMagazinFieldForm, MIZEditForm):
    ausgabe__magazin = forms.ModelChoiceField(
        required=False,
        label="Magazin",
        queryset=_models.Magazin.objects.all(),
        widget=make_widget(_models.Magazin),
        empty_label=None,
    )

    class Meta(MIZEditForm.Meta):
        model = _models.Artikel
        fields = forms.ALL_FIELDS
        widgets = {
            "schlagzeile": forms.Textarea(attrs={"class": "textarea-rows-2"}),
            "ausgabe": make_widget(_models.Ausgabe, tabular=True),
            "seitenumfang": forms.Select(choices=_models.Artikel.Umfang, attrs={"style": "max-width: 200px;"}),
        }


class AudioForm(DiscogsFormMixin, MIZEditForm):
    laufzeit = forms.DurationField(
        help_text="Beispiel Laufzeit von 144 Minuten: 0:144:0",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "hh:mm:ss", "style": "max-width: 200px;"}),
        label="Laufzeit",
    )

    url_field_name = "discogs_url"
    release_id_field_name = "release_id"

    class Meta(MIZEditForm.Meta):
        model = _models.Audio
        widgets = {"titel": forms.Textarea(attrs={"class": "textarea-rows-2"}), "original": boolean_select}
        fields = forms.ALL_FIELDS


class AutorForm(MinMaxRequiredFormMixin, MIZEditForm):
    minmax_required = [{"min_fields": 1, "fields": ["kuerzel", "person"]}]


class BuchForm(MinMaxRequiredFormMixin, MIZEditForm):
    minmax_required = [
        {
            "max_fields": 1,
            "fields": ["is_buchband", "buchband"],
            "error_messages": {"max": "Ein Sammelband kann nicht selber Teil eines Sammelbandes sein."},
        }
    ]

    class Meta(MIZEditForm.Meta):
        widgets = {
            "titel": forms.Textarea(attrs={"class": "textarea-rows-2"}),
            "titel_orig": forms.Textarea(attrs={"class": "textarea-rows-1"}),
            "is_buchband": boolean_select,
            "buchband": make_widget(_models.Buch, url="autocomplete_buchband"),
        }


class PersonForm(base_forms.PersonForm, MIZEditForm):  # type: ignore[misc]
    pass


class VideoForm(DiscogsFormMixin, MIZEditForm):
    url_field_name = "discogs_url"
    release_id_field_name = "release_id"

    class Meta(MIZEditForm.Meta):
        widgets = {
            "titel": forms.Textarea(attrs={"class": "textarea-rows-2"}),
            "original": boolean_select,
        }


class BrochureForm(AusgabeMagazinFieldForm, MIZEditForm):
    ausgabe__magazin = forms.ModelChoiceField(
        required=False,
        label="Magazin",
        queryset=_models.Magazin.objects.all(),
        widget=make_widget(_models.Magazin),
        empty_label=None,
    )

    class Meta(MIZEditForm.Meta):
        model = _models.Artikel
        fields = forms.ALL_FIELDS
        widgets = {"ausgabe": make_widget(_models.Ausgabe, tabular=True)}


class PlakatForm(MIZEditForm):
    plakat_id = forms.CharField(
        label="Plakat ID",
        disabled=True,
        required=False,
        help_text=(
            "Die ID wird von der Datenbank nach Abspeichern vergeben und "
            "muss auf der Rückseite des Plakats vermerkt werden."
        ),
    )

    class Meta(MIZEditForm.Meta):
        model = _models.Plakat
        fields = forms.ALL_FIELDS

    def __init__(self, *args, **kwargs):  # pragma: no cover
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.initial["plakat_id"] = "P" + str(self.instance.pk).zfill(6)


class FotoForm(MIZEditForm):
    foto_id = forms.CharField(
        label="Foto ID",
        disabled=True,
        required=False,
        help_text=(
            "Die ID wird von der Datenbank nach Abspeichern vergeben und "
            "muss auf der Rückseite des Fotos vermerkt werden."
        ),
    )

    class Meta(MIZEditForm.Meta):
        model = _models.Plakat
        fields = forms.ALL_FIELDS

    def __init__(self, *args, **kwargs):  # pragma: no cover
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.initial["foto_id"] = str(self.instance.pk).zfill(6)


################################################################################
# INLINE FORMS
################################################################################


class InlineForm(InlineFormBase):
    class Media:
        js = ["mizdb/js/inlines_scroll.js", "mizdb/js/inlines_changelist_btn.js"]

    class Meta:
        formfield_callback = inline_formfield_callback


class BestandInlineForm(InlineForm):
    class Meta(InlineForm.Meta):
        widgets = {
            "provenienz": make_widget(_models.Provenienz, can_remove=True),  # enable remove button
            "anmerkungen": forms.Textarea(attrs={"class": "textarea-rows-1"}),
        }


class AusgabeInlineForm(InlineForm):
    ausgabe__magazin = forms.ModelChoiceField(
        required=False,
        label="Magazin",
        queryset=_models.Magazin.objects.all(),
        widget=make_widget(_models.Magazin),
        empty_label=None,
    )

    class Meta(InlineForm.Meta):
        widgets = {"ausgabe": make_widget(_models.Ausgabe, tabular=True)}

    def __init__(self, *args, **kwargs):
        """Set the initial for ausgabe__magazin according to the form's instance."""
        if "instance" in kwargs and kwargs["instance"]:
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            if kwargs["instance"].ausgabe:
                kwargs["initial"]["ausgabe__magazin"] = kwargs["instance"].ausgabe.magazin
        super().__init__(*args, **kwargs)


################################################################################
# SEARCH FORMS
################################################################################


class MusikerSearchForm(SearchForm):
    """
    Search form for the Musiker changelist with an additional search field for
    'Bands'.
    """

    # The search form's algorithm for finding relations ignores the relation
    # from Musiker to Band (flags it as "reverse" and "not supported"). Instead
    # of reworking the algorithm, declare the field separately:
    band = forms.ModelMultipleChoiceField(
        required=False,
        label="Bands",
        queryset=_models.Band.objects.all(),
        widget=make_widget(_models.Band, multiple=True),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookups["band"] = ["in"]


################################################################################
# SEND FEEDBACK FORM
################################################################################


class FeedbackForm(forms.Form):
    subject = forms.CharField(label="Titel")
    message = forms.CharField(
        label="Nachricht",
        widget=forms.Textarea(attrs={"class": "textarea-rows-4", "placeholder": "Deine Nachricht an die Admins"}),
    )
    email = forms.EmailField(
        label="Deine E-Mail Adresse",
        widget=forms.EmailInput(attrs={"placeholder": "Optional"}),
        required=False,
        help_text="Wenn du möchtest, dass du per E-Mail eine Antwort bekommst, kannst du hier deine E-Mail Adresse angeben.",
    )
