#

from django.template import Library
from django.contrib.admin.utils import get_fields_from_path
from django.contrib.admin.views.main import SEARCH_VAR
from django.db.models.fields import BooleanField

register = Library()

@register.inclusion_tag("admin/advanced_search_form.html")
def advanced_search_form(cl):
    model_admin = cl.model_admin
    model = cl.model
    params = cl.params
    asf_dict = getattr(model_admin, 'advanced_search_form', None)
    asf = dict(selects=[], gtelt=[], simple=[])
    if asf_dict:
        for item in asf_dict.get('selects', []):
            field = get_fields_from_path(model, item)[0]
            field_choices = field.get_choices() #returns tuple(pk,name)
            choices = []
            for pk, name in field_choices:
                choices.append(dict(pk=pk, display=name, selected=params.get(field.attname, 0)==str(pk)))
            
            asf['selects'].append( dict(
                    label               = get_fields_from_path(model, item)[-1].verbose_name, 
                    query_string        = field.attname, 
                    choices             = choices, 
                )
            )
                
        for item in asf_dict.get('gtelt', []):
            asf['gtelt'].append( dict(
                    label               = get_fields_from_path(model, item)[-1].verbose_name, 
                    gte_query_string    = item+"__gte", 
                    gte_val             = params.get(item+"__gte", None) or params.get(item, ''), 
                    lt_query_string     = item+"__lt", 
                    lt_val              = params.get(item+"__lt", ''), 
               )
            )
        for item in asf_dict.get('simple', []):
            field = get_fields_from_path(model, item)[-1]
            asf['simple'].append( dict(
                    label               = field.verbose_name,
                    query_string        = item, 
                    val                 = item in params, 
                    bool                = isinstance(field, BooleanField)
                )
            )
            
    return {
        'asf' : asf, 
        'cl': cl,
        'show_result_count': cl.result_count != cl.full_result_count,
        'search_var': SEARCH_VAR
    }
