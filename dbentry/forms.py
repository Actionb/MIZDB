from typing import Any

# noinspection PyPackageRequirements
from dal import autocomplete
from django import forms
from django.contrib.admin.widgets import AdminTextInputWidget
from django.core.exceptions import ValidationError

from dbentry import models as _models
from dbentry.admin.autocomplete.widgets import make_widget
from dbentry.base.forms import DiscogsFormMixin, MinMaxRequiredFormMixin
from dbentry.utils.gnd import searchgnd
from dbentry.validators import DNBURLValidator


class GoogleBtnWidget(AdminTextInputWidget):
    """
    A TextInput widget with a button which opens a Google search for the text
    in the TextInput widget.
    """

    template_name = "googlebuttonwidget.html"

    class Media:
        js = ("mizdb/js/googlebtn.js",)


class AusgabeMagazinFieldForm(forms.ModelForm):
    """
    A model form that adds a choice field for a Magazin instance, to limit the
    available choices of Ausgabe instances for the field 'ausgabe' (forwarding).

    Also adds the Ausgabe's magazin to the form's initial data (if applicable).
    """

    ausgabe__magazin = forms.ModelChoiceField(
        required=False,
        label="Magazin",
        queryset=_models.Magazin.objects.all(),
        widget=make_widget(wrap=True, can_delete_related=False, model=_models.Magazin),
    )

    class Meta:
        widgets = {
            "ausgabe": make_widget(
                model_name="ausgabe", forward=["ausgabe__magazin"], tabular=True, attrs={"style": "width: 720px;"}
            ),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Set the initial for ausgabe__magazin according to the form's instance."""
        if "instance" in kwargs and kwargs["instance"]:
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            if kwargs["instance"].ausgabe:
                kwargs["initial"]["ausgabe__magazin"] = kwargs["instance"].ausgabe.magazin
        super().__init__(*args, **kwargs)


class ArtikelForm(AusgabeMagazinFieldForm):
    class Meta:
        model = _models.Artikel
        fields = "__all__"
        widgets = {
            "ausgabe": make_widget(
                model_name="ausgabe", forward=["ausgabe__magazin"], tabular=True, attrs={"style": "max-width: 720px;"}
            ),
            "schlagzeile": forms.Textarea(attrs={"rows": 2, "cols": 90}),
        }


class AutorForm(MinMaxRequiredFormMixin, forms.ModelForm):
    minmax_required = [{"min_fields": 1, "fields": ["kuerzel", "person"]}]


class BestandInlineForm(forms.ModelForm):
    class Meta:
        model = _models.Bestand
        fields = "__all__"
        widgets = {"anmerkungen": forms.Textarea(attrs={"rows": 1, "cols": 30})}


class BrochureForm(AusgabeMagazinFieldForm):
    class Meta:
        widgets = {
            "ausgabe": make_widget(
                model_name="ausgabe", forward=["ausgabe__magazin"], tabular=True, attrs={"style": "width: 720px;"}
            ),
            "titel": forms.Textarea(attrs={"rows": 1, "cols": 90}),
        }


class BuchForm(MinMaxRequiredFormMixin, forms.ModelForm):
    minmax_required = [
        {
            "max_fields": 1,
            "fields": ["is_buchband", "buchband"],
            "error_messages": {"max": "Ein Buchband kann nicht selber Teil eines Buchbandes sein."},
        }
    ]

    class Meta:
        widgets = {
            "titel": forms.Textarea(attrs={"rows": 1, "cols": 90}),
            "titel_orig": forms.Textarea(attrs={"rows": 1, "cols": 90}),
        }

    def clean_is_buchband(self) -> bool:
        """
        Only allow setting ``is_buchband`` to False for instances that aren't
        referenced by other Buch instances.

        If this form's instance was flagged as a Buchband and other Buch
        instances refer to it as their Buchband, setting is_buchband to False
        would end up making the forms of the related instances invalid:
        the selected Buchband would not be a valid choice anymore as the choices
        are limited to {'is_buchband': True} (see the model field).
        """
        is_buchband = self.cleaned_data.get("is_buchband", False)
        if not is_buchband and self.instance.pk and self.instance.buch_set.exists():
            raise ValidationError("Nicht abwählbar für Buchband mit existierenden Aufsätzen.", code="invalid")
        return is_buchband


class MusikerForm(forms.ModelForm):
    class Meta:
        widgets = {"kuenstler_name": GoogleBtnWidget()}


class BandForm(forms.ModelForm):
    class Meta:
        widgets = {"band_name": GoogleBtnWidget()}


class AudioForm(DiscogsFormMixin, forms.ModelForm):
    url_field_name = "discogs_url"
    release_id_field_name = "release_id"

    class Meta:
        widgets = {"titel": forms.Textarea(attrs={"rows": 1, "cols": 90})}


class VideoForm(DiscogsFormMixin, forms.ModelForm):
    url_field_name = "discogs_url"
    release_id_field_name = "release_id"

    class Meta:
        widgets = {"titel": forms.Textarea(attrs={"rows": 1, "cols": 90})}


class PlakatForm(forms.ModelForm):
    """
    The form for the Plakat admin add/change page.

    A BooleanField is added with which the user can request to copy all related
    Musiker/Band objects of the related Veranstaltung instances to this
    Plakat instance.
    """

    copy_related = forms.BooleanField(
        label="Bands/Musiker kopieren",
        help_text=(
            "Setzen Sie das Häkchen, um Bands und Musiker der "
            "Veranstaltungen direkt zu diesem Datensatz hinzuzufügen."
        ),
        required=False,
    )

    class Meta:
        widgets = {"titel": forms.Textarea(attrs={"rows": 1, "cols": 90})}
        help_texts = {
            "plakat_id": (
                "Die ID wird von der Datenbank nach Abspeichern vergeben und "
                "muss auf der Rückseite des Plakats vermerkt werden."
            )
        }


class FotoForm(forms.ModelForm):
    class Meta:
        widgets = {"titel": forms.Textarea(attrs={"rows": 1, "cols": 90})}
        help_texts = {
            "foto_id": (
                "Die ID wird von der Datenbank nach Abspeichern vergeben und "
                "muss auf der Rückseite des Fotos vermerkt werden."
            )
        }


class PersonForm(forms.ModelForm):
    class Meta:
        widgets = {"gnd_id": autocomplete.Select2(url="gnd"), "gnd_name": forms.HiddenInput()}

    url_validator_class = DNBURLValidator

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "dnb_url" in self.fields:
            self.fields["dnb_url"].validators.append(self.url_validator_class())
            # Add a link to the search form of the DNB to the help text:
            self.fields["dnb_url"].help_text = (
                "Adresse zur Seite dieser Person in der "
                '<a href="https://portal.dnb.de/opac/checkCategory?categoryId=persons" target="_blank">'  # noqa
                "Deutschen Nationalbibliothek</a>."
            )
        if self.instance.pk and "gnd_id" in self.fields:
            # Set the choice selected in the widget:
            self.fields["gnd_id"].widget.choices = [(self.instance.gnd_id, self.instance.gnd_name)]

    def clean(self) -> dict:
        """Validate and clean gnd_id and dnb_url."""
        if "dnb_url" in self._errors or "gnd_id" in self._errors:  # pragma: no cover
            return self.cleaned_data

        gnd_id = self.cleaned_data.get("gnd_id", "")
        dnb_url = self.cleaned_data.get("dnb_url", "")

        if not (gnd_id or dnb_url):
            return self.cleaned_data

        match = self.url_validator_class.regex.search(dnb_url)
        if match and len(match.groups()) == 1:
            # The URL is valid and has a gnd_id.
            # The validator doesn't allow URLs without at least a one-digit ID.
            gnd_id_from_url = match.groups()[-1]

            if "gnd_id" in self.changed_data and "dnb_url" in self.changed_data:
                if not gnd_id:
                    # gnd_id was 'removed'. Set it from the new URL.
                    gnd_id = gnd_id_from_url
                    self.cleaned_data["gnd_id"] = gnd_id
                elif gnd_id_from_url != gnd_id:
                    # The values of both fields have changed, but the IDs do
                    # not match.
                    raise ValidationError(
                        "Die angegebene GND ID (%s) stimmt nicht mit der ID im "
                        "DNB Link überein (%s)." % (gnd_id, gnd_id_from_url)
                    )
            elif "dnb_url" in self.changed_data or not gnd_id:
                # Only dnb_url was changed; update gnd_id accordingly.
                gnd_id = gnd_id_from_url
                self.cleaned_data["gnd_id"] = gnd_id

        # Validate the gnd_id by checking that an SRU query with it returns
        # a single match.
        results, _c = searchgnd(query="nid=" + gnd_id)
        if len(results) != 1:
            raise ValidationError("Die GND ID ist ungültig.")
        # Store the result's label for later use as data for the model field
        # 'gnd_name'.
        self.cleaned_data["gnd_name"] = results[0][1]
        # Normalize the URL to the DNB permalink.
        dnb_url = "http://d-nb.info/gnd/" + gnd_id
        self.cleaned_data["dnb_url"] = dnb_url
        return self.cleaned_data
