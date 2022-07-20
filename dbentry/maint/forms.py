from typing import Any, Callable, List, Tuple, Type

from django import forms
from django.apps import apps
from django.contrib.admin import AdminSite
from django.db.models import Model
from django.db.models.constants import LOOKUP_SEP

from dbentry import utils
from dbentry.base.forms import DynamicChoiceFormMixin, MIZAdminForm
from dbentry.sites import miz_site


class DuplicateFieldsSelectForm(forms.Form):
    """
    A form to select the model fields that are going to be used in the search
    for duplicates, and the fields whose values should be displayed in the
    overview.
    """

    select = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)
    display = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)

    class Media:
        css = {'all': ['admin/css/forms.css']}
        js = ['admin/js/collapse.js']

    def __init__(self, *, model: Type[Model], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fields['select'].choices, self.fields['display'].choices = (
            get_dupe_field_choices(model)
        )


def get_dupe_field_choices(model: Type[Model]) -> Tuple:
    """
    Return the choices for the 'select' and the 'display' fields of the
    DuplicateFieldsSelectForm for the given model.

    Include all concrete, non-blank, non-m2m fields in the choices for
    'select': the values of those fields can be used to identify duplicates.
    Include every field and relation in choices for 'display'.
    """
    select_choices, display_choices = [], []
    m2m, reverse = [], []
    # noinspection PyUnresolvedReferences
    for field in model._meta.get_fields():
        if field.concrete:
            if field.primary_key:
                continue
            if field.many_to_many:
                # Add a choice for the related model's name_field, but add them
                # to display_choices after all non-m2m choices.
                target = getattr(field.related_model, 'name_field', '') or 'pk'
                m2m.append((
                    field.name + LOOKUP_SEP + target,
                    field.verbose_name.capitalize()
                ))
            else:
                choice = (field.name, field.verbose_name.capitalize())
                display_choices.append(choice)
                if not field.blank:
                    # A concrete, non-blank, non-m2m field.
                    select_choices.append(choice)
        else:
            # Some kind of reverse relation. Add a choice for the related
            # model's name_field.
            target = getattr(field.related_model, 'name_field', '') or 'pk'
            reverse.append((
                utils.get_reverse_field_path(field, target),
                field.related_model._meta.verbose_name
            ))
    display_choices.extend([*sorted(m2m), *sorted(reverse)])
    return select_choices, display_choices


class ModelSelectForm(DynamicChoiceFormMixin, MIZAdminForm):
    """
    A form to select a model with.

    The choices of the only formfield ``model_select`` are the models of the
    given app which are also registered with the given admin site.
    """

    model_select = forms.ChoiceField(label='Bitte Tabelle auswählen')

    def __init__(
            self,
            *args: Any,
            app_label: str = 'dbentry',
            admin_site: AdminSite = miz_site,
            **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.app_label = app_label
        self.admin_site = admin_site
        self.fields['model_select'].choices = self.get_model_list()

    def get_model_filters(self) -> List[Callable[[Type[Model]], bool]]:
        """Prepare filters for the list of models returned by apps.get_models."""
        return [
            # Filter out models that are not of this app:
            lambda model: model._meta.app_label == self.app_label,
            # Filter out models that are not registered with the admin site:
            lambda model: self.admin_site.is_registered(model),
        ]

    def get_model_list(self) -> List[Tuple[str, str]]:
        """Return the choices for the ``model_select`` field."""
        filters = self.get_model_filters()
        choices = [
            (model._meta.model_name, model._meta.verbose_name)
            for model in utils.nfilter(filters, apps.get_models(self.app_label))
        ]
        # Sort the choices by verbose_name.
        return sorted(choices, key=lambda tpl: tpl[1])


class UnusedObjectsForm(ModelSelectForm):
    """Form for UnusedObjectsView."""

    limit = forms.IntegerField(label="Grenzwert", min_value=0, initial=0)
