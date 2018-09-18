
from django.template import Library
from django.contrib.admin.utils import get_fields_from_path
from django.contrib.admin.views.main import SEARCH_VAR
from django.db.models.fields import BooleanField

register = Library()

@register.inclusion_tag("admin/advanced_search_form.html")
def advanced_search_form(cl):
    model_admin = cl.model_admin
    model = cl.model
    params = cl.request.GET.copy()
    
    full_count = cl.model_admin.model._meta.default_manager.count()
    
    asf_dict = getattr(model_admin, 'advanced_search_form', {})
    labels = asf_dict.get('labels', {})
    # See if we can add a form with autocomplete functionality:
    from DBentry.advsfforms import advSF_factory
    form = advSF_factory(model_admin, labels=asf_dict.get('labels', {}))
    
    if form:
        form = form(initial=params)
        form_fields = form.base_fields
    else:
        form_fields = {}
        
    asf = dict(selects=[], gtelt=[], simple=[], ac_form=form)
    if asf_dict:
        for item in asf_dict.get('selects', []):
            if isinstance(item, (list, tuple)):
                item, forward = item
            field = get_fields_from_path(model, item)[-1]
            if item in form_fields or getattr(field, 'name', None) in form_fields:
                # Ignore items that are already being handled by the form
                continue
            #TODO: use field.get_choices(limit_choices_to={'pk__in':some_set}) to limit choices (duh)
            #Maybe do this in autocomplete views?
            field_choices = field.get_choices() 
            choices = []
            for pk, name in field_choices:
                choices.append(dict(pk=pk, display=name, selected=params.get(field.attname, 0)==str(pk)))
            asf['selects'].append( dict(
                    label               = labels.get(item) or field.verbose_name,  #get_fields_from_path(model, item)[-1].verbose_name, 
                    query_string        = field.attname, 
                    choices             = choices, 
                )
            )
        # 2 Text inputs: greater than x and less than y
        for item in asf_dict.get('gtelt', []): #TODO: this adds an 'empty' div if there are no items in gtelt
            asf['gtelt'].append( dict(
                    label               = labels.get(item, None) or get_fields_from_path(model, item)[-1].verbose_name, 
                    gte_query_string    = item+"__gte", 
                    gte_val             = params.get(item+"__gte", None) or params.get(item, ''), 
                    lt_query_string     = item+"__lt", 
                    lt_val              = params.get(item+"__lt", ''), 
               )
            )
        # Simple text/bool inputs
        for item in asf_dict.get('simple', []):
            field = get_fields_from_path(model, item)[-1]
            asf['simple'].append( dict(
                    label               = labels.get(item, None) or field.verbose_name,
                    query_string        = item, 
                    val                 = params.get(item, ''), 
                    bool                = isinstance(field, BooleanField)
                )
            )
    return {
        'asf' : asf, 
        'cl': cl,
        'full_count' : full_count, 
        'show_result_count': full_count == cl.result_count,
        'search_var': SEARCH_VAR
    }
    
@register.filter
def tabindex(value, index):
    """
    Add a tabindex attribute to the widget for a bound field.
    Credit for idea to: Gareth Reese (stackoverflow)
    """
    value.field.widget.attrs['tabindex'] = index
    return value
