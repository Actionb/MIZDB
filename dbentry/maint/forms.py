from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Type

from django import forms
from django.apps import apps
from django.db.models import Model
from django.forms import BoundField

from dbentry import utils
from dbentry.base import models as base_models
from dbentry.base.forms import (DynamicChoiceFormMixin, MIZAdminForm, MinMaxRequiredFormMixin)


class DuplicateFieldsSelectForm(MinMaxRequiredFormMixin, forms.Form):
    """
    A form to select the model fields that are going to be used in the search
    for duplicates.

    The model fields are separated into three categories:
        ``base``: concrete model fields that are not ManyToManyFields
        ``m2m``: concrete model fields that are ManyToManyFields
        ``reverse``: reverse ManyToOne relations to this model
    The choices for each MultipleChoiceField are created with the function
    ``get_dupe_fields_for_model``.
    """

    base = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label=''
    )
    m2m = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label=''
    )
    reverse = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label=''
    )

    base_display = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label=''
    )
    m2m_display = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label=''
    )
    reverse_display = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label=''
    )
    minmax_required = [
        {
            'min_fields': 1,
            'fields': ['base', 'm2m', 'reverse'],
            'error_messages': {
                'min': 'Bitte mindestens ein Feld für die Duplikatensuche auswählen.'
            }
        },
        {
            'min_fields': 1,
            'fields': ['base_display', 'm2m_display', 'reverse_display'],
            'error_messages': {
                'min': 'Bitte mindestens ein Feld für die Übersicht auswählen.'
            }
        }
    ]

    class Media:
        css = {'all': ['admin/css/forms.css']}
        js = ['admin/js/collapse.js']

    def __init__(self, *, model: Type[Model], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        choices = get_dupe_fields_for_model(model)
        self.fields['base'].choices = choices['base']
        self.fields['m2m'].choices = choices['m2m']
        self.fields['reverse'].choices = choices['reverse']
        self.fields['base_display'].choices = choices['base']
        self.fields['m2m_display'].choices = choices['m2m']
        self.fields['reverse_display'].choices = choices['reverse']
        self.select_fields = ['base', 'm2m', 'reverse']
        self.display_fields = ['base_display', 'm2m_display', 'reverse_display']

    def selects(self) -> Iterator[BoundField]:
        """Return the bound fields of the dupe field selection."""
        for name in self.select_fields:
            yield self[name]

    def displays(self) -> Iterator[BoundField]:
        """Return the bound fields for the display field selection."""
        for name in self.display_fields:
            yield self[name]


def get_dupe_fields_for_model(model: Type[Model]) -> Dict[str, list]:
    """
    Prepare the choices for the three categories of DuplicateFieldsSelectForm.

    Returns a dictionary of {category_name: choices}.
    """
    # TODO: this misses 'bands' for model 'Musiker'
    base = [
        (f.name, f.verbose_name.capitalize())
        for f in utils.get_model_fields(model, base=True, foreign=True, m2m=False)
    ]
    m2m = [
        (f.name, f.verbose_name.capitalize())
        for f in utils.get_model_fields(model, base=False, foreign=False, m2m=True)
    ]

    # Group the choices by the related_model's verbose_name:
    # ( (<group_name>,(<group_choices>,)), ... )
    groups = []
    for rel in utils.get_model_relations(model, forward=False, reverse=True):
        if rel.many_to_many:
            continue
        related_model = rel.related_model
        group_choices = []
        model_fields = utils.get_model_fields(
            related_model,
            base=True, foreign=True, m2m=False,
            exclude=['_fts']
        )
        for field in model_fields:
            if field.remote_field == rel:
                # This is the foreign key field that brought us here to begin
                # with; don't include it.
                continue
            # The value for this choice should be the field path that follows
            # this reverse relation (i.e. from related model to the field).
            group_choices.append(
                (
                    utils.get_reverse_field_path(rel, field.name),
                    field.verbose_name.capitalize()
                )
            )
        if group_choices:
            groups.append(
                (
                    related_model._meta.verbose_name,
                    group_choices
                )
            )
    # get_model_relations uses an unordered set() to collect the relations;
    # We need to sort the group names alphabetically to establish some order.
    groups = sorted(groups, key=lambda group: group[0].lower())
    return {'base': base, 'm2m': m2m, 'reverse': groups}


class ModelSelectForm(DynamicChoiceFormMixin, MIZAdminForm):
    """
    A form to select a model with.

    The choices of the only formfield ``model_select`` are the model names and
    their verbose names as returned by apps.get_models, filtered with filters
    provided by the form instance's ``get_model_filters`` method.
    The attribute ``exclude_models`` is a list of model names that are to be
    filtered out.
    """

    model_select = forms.ChoiceField(
        initial='',
        label='Bitte Tabelle auswählen'
    )
    # Exclude some models that are a bit... different.
    exclude_models = [
        'ausgabenum', 'ausgabelnum', 'ausgabemonat',
    ]

    def __init__(
            self,
            *args: Any,
            exclude: Optional[List[str]] = None,
            app_label: str = 'dbentry',
            **kwargs: Any
    ) -> None:
        if exclude:
            self.exclude_models = exclude
        self.app_label = app_label
        choices = {'model_select': self.get_model_list()}
        super().__init__(choices=choices, *args, **kwargs)

    def get_model_filters(self) -> List[Callable[[Type[Model]], bool]]:
        """
        Prepare filters for the list of models returned by apps.get_models.
        """
        return [
            # Filter out m2m intermediary tables (manually or auto created)
            # and models inherited from other apps.
            lambda model: (
                    issubclass(model, base_models.BaseModel)
                    and not issubclass(model, base_models.BaseM2MModel)),
            # <model>_alias tables can contain as many duplicates as they want.
            lambda model: not model._meta.model_name.endswith('_alias'),
            lambda model: model._meta.model_name not in self.exclude_models
        ]

    def get_model_list(self) -> List[Tuple[str, str]]:
        """Return the choices for the ``model_select`` field."""
        filters = self.get_model_filters()
        choices = [
            (model._meta.model_name, model._meta.object_name)
            for model in utils.nfilter(filters, apps.get_models(self.app_label))
        ]
        # Sort the choices by verbose_name.
        return sorted(choices, key=lambda tpl: tpl[1])


class UnusedObjectsForm(ModelSelectForm):
    """Form for UnusedObjectsView."""

    limit = forms.IntegerField(label="Grenzwert", min_value=0, initial=0)
