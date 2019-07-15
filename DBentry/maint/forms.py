from django import forms 

from DBentry.base.forms import MIZAdminForm 
from DBentry.utils import get_model_fields, get_model_relations, get_reverse_field_path

class DuplicateFieldsSelectForm(forms.Form): 
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
    
class ModelSelectForm(MIZAdminForm):
    
    def get_model_list():
        #TODO: review this
        from django.apps import apps
        rslt = []
        for model in apps.get_models('DBentry'):
            if model.__module__ == 'DBentry.models' and not model._meta.auto_created\
            and 'alias' not in model._meta.model_name\
            and model._meta.verbose_name not in ('favoriten', 'lfd. Nummer', 'Ausgabe-Monat', 'Nummer'):
                rslt.append((model._meta.model_name, model._meta.verbose_name))
        return [('', '')] + sorted(rslt, key=lambda tpl:tpl[1])
        
    model_select = forms.ChoiceField(choices = get_model_list, label = 'Bitte das Modell auswählen', initial = '')
