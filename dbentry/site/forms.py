from django import forms
from django.db import models
from django.forms.models import ModelFormMetaclass

from dbentry import forms as base_forms
from dbentry import models as _models
from dbentry.autocomplete.widgets import make_widget
from dbentry.base.forms import DiscogsFormMixin, MinMaxRequiredFormMixin, MIZAdminInlineFormBase
from dbentry.forms import AusgabeMagazinFieldForm
from dbentry.site.widgets import MIZURLInput

boolean_select = forms.Select(choices=[(True, "Ja"), (False, "Nein")])
null_boolean_select = forms.Select(choices=[(None, "---------"), (True, "Ja"), (False, "Nein")])


# TODO: Move formfield_callback into MIZEditForm/InlineForm._meta after
#  upgrading to Django 4.2.
#  In 4.2, ModelForm accepts a Meta option formfield_callback to customize form fields.
#  https://docs.djangoproject.com/en/4.2/releases/4.2/#forms


class EditFormMetaclass(ModelFormMetaclass):
    """
    Form metaclass that provides a formfield_callback which sets M2M fields to
    not required.
    """

    @staticmethod
    def formfield_callback(field, **kwargs):
        if isinstance(field, models.ManyToManyField):
            kwargs["required"] = False
            if "widget" not in kwargs:
                kwargs["widget"] = make_widget(field.related_model, multiple=True)
        if isinstance(field, models.ForeignKey):
            kwargs["empty_label"] = None
            if "widget" not in kwargs:
                kwargs["widget"] = make_widget(field.related_model, can_remove=field.blank)
        if isinstance(field, models.URLField):
            if "widget" not in kwargs:
                kwargs["widget"] = MIZURLInput
        return field.formfield(**kwargs)

    def __new__(mcs, name, bases, attrs):
        attrs["formfield_callback"] = mcs.formfield_callback
        return super().__new__(mcs, name, bases, attrs)


class MIZEditForm(forms.ModelForm, metaclass=EditFormMetaclass):
    """
    Base class for edit forms.

    The metaclass assigns autocomplete widgets to relation fields.
    The metaclass sets M2M fields to not required.
    """


class InlineFormMetaclass(ModelFormMetaclass):
    """Form metaclass that disables the 'remove' button on mizselect items."""

    @staticmethod
    def formfield_callback(field, **kwargs):
        if isinstance(field, models.ManyToManyField):
            kwargs["required"] = False
            if "widget" not in kwargs:
                kwargs["widget"] = make_widget(field.related_model, multiple=True)
        if isinstance(field, models.ForeignKey):
            kwargs["empty_label"] = None
            if "widget" not in kwargs:
                kwargs["widget"] = make_widget(field.related_model, can_remove=False)
        if isinstance(field, models.URLField):
            if "widget" not in kwargs:
                kwargs["widget"] = MIZURLInput
        return field.formfield(**kwargs)

    def __new__(mcs, name, bases, attrs):
        attrs["formfield_callback"] = mcs.formfield_callback
        return super().__new__(mcs, name, bases, attrs)


class ArtikelForm(AusgabeMagazinFieldForm, MIZEditForm):
    ausgabe__magazin = forms.ModelChoiceField(
        required=False,
        label="Magazin",
        queryset=_models.Magazin.objects.all(),
        widget=make_widget(_models.Magazin),
        empty_label=None,
    )

    class Meta:
        model = _models.Artikel
        fields = forms.ALL_FIELDS
        widgets = {
            "schlagzeile": forms.Textarea(attrs={"class": "textarea-rows-1"}),
            "ausgabe": make_widget(_models.Ausgabe, tabular=True),
            "seitenumfang": forms.Select(choices=_models.Artikel.Umfang, attrs={"style": "max-width: 200px;"}),
        }


class AudioForm(DiscogsFormMixin, MIZEditForm):
    laufzeit = forms.DurationField(
        help_text="Beispiel Laufzeit von 144 Minuten: 0:144:0",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "hh:mm:ss", "style": "max-width: 200px;"}),
    )

    url_field_name = "discogs_url"
    release_id_field_name = "release_id"

    class Meta:
        model = _models.Audio
        widgets = {"titel": forms.Textarea(attrs={"class": "textarea-rows-1"}), "original": boolean_select}
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

    class Meta:
        widgets = {
            "titel": forms.Textarea(attrs={"class": "textarea-rows-1"}),
            "titel_orig": forms.Textarea(attrs={"class": "textarea-rows-1"}),
            "is_buchband": boolean_select,
            "buchband": make_widget(_models.Buch, url="autocomplete_buchband"),
        }


class PersonForm(base_forms.PersonForm, MIZEditForm):
    pass


class VideoForm(DiscogsFormMixin, MIZEditForm):
    url_field_name = "discogs_url"
    release_id_field_name = "release_id"

    class Meta:
        widgets = {
            "titel": forms.Textarea(attrs={"class": "textarea-rows-1"}),
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

    class Meta:
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

    class Meta:
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

    class Meta:
        model = _models.Plakat
        fields = forms.ALL_FIELDS

    def __init__(self, *args, **kwargs):  # pragma: no cover
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.initial["foto_id"] = str(self.instance.pk).zfill(6)


################################################################################
# INLINE FORMS
################################################################################


class InlineForm(MIZAdminInlineFormBase, metaclass=InlineFormMetaclass):
    class Media:
        js = ["mizdb/js/inlines_scroll.js"]


class BestandInlineForm(InlineForm):
    class Meta:
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

    class Meta:
        widgets = {"ausgabe": make_widget(_models.Ausgabe, tabular=True)}
