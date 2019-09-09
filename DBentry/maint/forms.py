from django import forms
from django.apps import apps

from DBentry.base import models as base_models
from DBentry.base.forms import MIZAdminForm, DynamicChoiceFormMixin
from DBentry.utils import (
    get_model_fields, get_model_relations, get_reverse_field_path, nfilter
)

class DuplicateFieldsSelectForm(forms.Form): 
    #TODO: this doesn't use DynamicChoiceFormMixin despite it assigning choices after creation
    base = forms.MultipleChoiceField(widget = forms.CheckboxSelectMultiple, label = '')
    m2m = forms.MultipleChoiceField(widget = forms.CheckboxSelectMultiple, label = '')
    reverse = forms.MultipleChoiceField(widget = forms.CheckboxSelectMultiple, label = '')

    help_text ='Wähle die Felder, deren Werte in die Suche miteinbezogen werden sollen.'

    class Media:
        css = {'all':  ['admin/css/dupes.css']}
        js = ['admin/js/collapse.js'] #TODO: django changed how it adds events to collapse stuff; check it out

def get_dupe_fields_for_model(model):    
    """
    Returns two-tuples of (queryable field path, field label) of fields that can be used to find duplicates with.
    """
    base = [
        (f.name, f.verbose_name.capitalize())
        for f in get_model_fields(model, base = True, foreign = True,  m2m = False)
    ]
    m2m = [
        (f.name, f.verbose_name.capitalize()) 
        for f in get_model_fields(model, base = False, foreign = False,  m2m = True)
    ]

    # Group the choices by the related_model's verbose_name:
    # ( (<group_name>,(<group_choices>,)), ... )
    groups = []            
    for rel in get_model_relations(model, forward= False,  reverse =True):
        if rel.many_to_many:
            continue
        related_model = rel.related_model
        group_choices = []
        for field in get_model_fields(related_model, base = True, foreign = True,  m2m = False):
            if field.remote_field == rel:
                # This is the foreign key field that brought us here to begin with;
                # don't include it
                continue
            group_choices.append((get_reverse_field_path(rel, field.name), field.verbose_name.capitalize()))
        if group_choices:
            group = (related_model._meta.verbose_name, group_choices)
            groups.append(group)
    # get_model_relations uses an unordered set() to collect the rels;
    # We need to sort everything alphabetically again to achieve some order
    order_by_group_name = lambda group: group[0].lower()
    groups = sorted(groups, key = order_by_group_name)
    return {'base': base, 'm2m': m2m, 'reverse': groups}

def duplicatefieldsform_factory(model, selected_dupe_fields):
    choices = get_dupe_fields_for_model(model)
    initial = {
            'base': [f for f in selected_dupe_fields if f in choices['base']], 
            'm2m': [f for f in selected_dupe_fields if f in choices['m2m']], 
            'reverse': [f for f in selected_dupe_fields if f in choices['reverse']], 
        }
    form = DuplicateFieldsSelectForm(initial = initial)
    form.fields['base'].choices = choices['base']
    form.fields['m2m'].choices = choices['m2m']
    form.fields['reverse'].choices = choices['reverse']
    return form

class ModelSelectForm(DynamicChoiceFormMixin, MIZAdminForm):

    # FIXME: commit 3c6b2c857254875d4e8b5d6ee298e921ab16e05b dropped the damn 'model_select' formfield!

    def __init__(self, model_filters = None, *args, **kwargs):
        choices = {'model_select': self.get_model_list(model_filters)}
        super().__init__(choices = choices, *args, **kwargs)

    _model_name_excludes = [
        'Favoriten', 'ausgabe_num', 'ausgabe_lnum', 'ausgabe_monat', 
    ]

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
            for model in nfilter(filters, apps.get_models('DBentry'))
        ]
        # Sort the choices by verbose_name.
        return sorted(choices, key=lambda tpl: tpl[1])
