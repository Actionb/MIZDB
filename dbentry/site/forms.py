from django import forms
from formset.renderers.bootstrap import FormRenderer
from formset.richtext.widgets import RichTextarea
from formset.widgets import Selectize

from dbentry import models as _models


class ArtikelForm(forms.ModelForm):
    default_renderer = FormRenderer(
        label_css_classes=("col-sm-3", "col-form-label"),
        control_css_classes=("col-sm-9",),
        field_css_classes={'*': 'row mb-3'},
    )

    magazin = forms.ModelChoiceField(
        _models.Magazin.objects.all(),
        widget=Selectize(search_lookup='magazin_name__icontains'),
        required=False
    )

    class Meta:
        model = _models.Artikel
        fields = [
            'magazin', 'ausgabe', 'schlagzeile', 'seite', 'seitenumfang',
            'zusammenfassung'
        ]
        widgets = {
            'zusammenfassung': RichTextarea(),
            'ausgabe': Selectize(
                search_lookup='_name__icontains',
                filter_by={'magazin': 'magazin_id'}
            ),
        }
