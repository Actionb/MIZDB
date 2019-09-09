from django import forms
from django.apps import apps

from DBentry import utils
from DBentry.base import models as base_models
from DBentry.base.forms import MIZAdminForm, DynamicChoiceFormMixin


class DuplicateFieldsSelectForm(forms.Form):
    """
    A form to select the model fields that are going to be used in the search
    for duplicates.

    The model fields are separated into three categories:
        'base': concrete model fields that are not ManyToManyFields
        'm2m': concrete model fields that are ManyToManyFields
        'reverse': reverse ManyToOne relations to this model
    The choices for each MultipleChoiceField are created with the function
    'get_dupe_fields_for_model' and are set after initialization
    (see duplicatefieldsform_factory).
    """
    base = forms.MultipleChoiceField(
        widget = forms.CheckboxSelectMultiple,
        label = ''
    )
    m2m = forms.MultipleChoiceField(
        widget = forms.CheckboxSelectMultiple,
        label = ''
    )
    reverse = forms.MultipleChoiceField(
        widget = forms.CheckboxSelectMultiple,
        label = ''
    )
    help_text = 'Wähle die Felder, '
    'deren Werte in die Suche miteinbezogen werden sollen.'

    class Media:
        css = {'all':  ['admin/css/dupes.css']}
        js = ['admin/js/collapse.js']


def get_dupe_fields_for_model(model):
    """
    Prepare the choices for the three categories of DuplicateFieldsSelectForm.

    Returns a dictionary of {category_name: choices}.
    """
    base = [
        (f.name, f.verbose_name.capitalize())
        for f in utils.get_model_fields(model, base=True, foreign=True,  m2m=False)
    ]
    m2m = [
        (f.name, f.verbose_name.capitalize())
        for f in utils.get_model_fields(model, base=False, foreign=False,  m2m=True)
    ]

    # Group the choices by the related_model's verbose_name:
    # ( (<group_name>,(<group_choices>,)), ... )
    groups = []
    for rel in utils.get_model_relations(model, forward= False,  reverse =True):
        if rel.many_to_many:
            continue
        related_model = rel.related_model
        group_choices = []
        model_fields = utils.get_model_fields(
            related_model,
            base=True, foreign=True, m2m=False
        )
        for field in model_fields:
            if field.remote_field == rel:
                # This is the foreign key field that brought us here to begin
                # with; don't include it.
                continue
            # The value for this choice should be the field path that follows
            # this reverse relation (i.e. from related model to the field).
            group_choices.append((
                utils.get_reverse_field_path(rel, field.name),
                field.verbose_name.capitalize()
            ))
        if group_choices:
            groups.append((
                related_model._meta.verbose_name,
                group_choices
            ))
    # get_model_relations uses an unordered set() to collect the rels;
    # We need to sort the group names alphabetically to establish some order.
    groups = sorted(groups, key = lambda group: group[0].lower())
    return {'base': base, 'm2m': m2m, 'reverse': groups}


def duplicatefieldsform_factory(model, selected_dupe_fields):
    """
    Instantiate the DuplicateFieldsSelectForm and set the choices for its fields.

    The form's initial data is derived from field names provided in argument
    'selected_dupe_fields'.
    """
    choices = get_dupe_fields_for_model(model)
    initial = {
            'base': [f for f in selected_dupe_fields if f in choices['base']],
            'm2m': [f for f in selected_dupe_fields if f in choices['m2m']],
            'reverse': [f for f in selected_dupe_fields if f in choices['reverse']],
        }
    form = DuplicateFieldsSelectForm(initial=initial)
    # While DynamicChoiceFormMixin could be used to streamline the setting of
    # choices, this here is still quite a bit more straight forward.
    form.fields['base'].choices = choices['base']
    form.fields['m2m'].choices = choices['m2m']
    form.fields['reverse'].choices = choices['reverse']
    return form


class ModelSelectForm(DynamicChoiceFormMixin, MIZAdminForm):
    """A form to select the model that is checked for duplicates."""

    # FIXME: commit 3c6b2c857254875d4e8b5d6ee298e921ab16e05b dropped the damn 'model_select' formfield!
    # Exclude some models that would be nonsensical for a duplicates search.
    _model_name_excludes = [
        'Favoriten', 'ausgabe_num', 'ausgabe_lnum', 'ausgabe_monat',
    ]

    def __init__(self, model_filters = None, *args, **kwargs):
        choices = {'model_select': self.get_model_list(model_filters)}
        super().__init__(choices = choices, *args, **kwargs)


    def get_model_filters(self):
        """
        Prepare filters to apply to the list of models returned by apps.get_models.
        """
        return [
            # Filter out m2m intermediary tables (manually or auto created)
            # and models inherited from other apps.
            lambda model: (
                issubclass(model, base_models.BaseModel) and
                not issubclass(model, base_models.BaseM2MModel)),
            # <model>_alias tables can contain as many duplicates as they want.
            lambda model: not model._meta.model_name.endswith('_alias'),
            lambda model: model._meta.model_name not in self._model_name_excludes
        ]

    def get_model_list(self, filters = None):
        """Return the choices for the 'model_select' field."""
        if filters is None:
            filters = self.get_model_filters()
        choices = [
            (model._meta.model_name, model._meta.verbose_name)
            for model in utils.nfilter(filters, apps.get_models('DBentry'))
        ]
        # Sort the choices by verbose_name.
        return sorted(choices, key=lambda tpl: tpl[1])
