
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
    full_count = cl.model_admin.model._meta.default_manager.count()
    
    asf_dict = getattr(model_admin, 'advanced_search_form', {})

    # See if we can add a form with autocomplete functionality:
    from DBentry.advsfforms import advSF_factory
    form = advSF_factory(model_admin)
    
    form_initial = {}
    form_fields = form.base_fields if form else {}
    if form:
        form = form(initial=params)
        # Get the right order down ... the factory constructor jumbled it up
        form.order_fields(asf_dict.get('selects',None))
    asf = dict(selects=[], gtelt=[], simple=[], ac_form=form)
    if asf_dict:
        for item in asf_dict.get('selects', []):
            if item in form_fields:
                # Ignore items that are already being handled by the form
                continue
            field = get_fields_from_path(model, item)[0]
            field_choices = field.get_choices() 
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
