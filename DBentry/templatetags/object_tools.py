
from django.urls import reverse, exceptions
from django.template import Library

from DBentry.utils import get_model_admin_for_model, make_simple_link

register = Library()
    
@register.simple_tag
def favorites_link(model_opts, is_popup = False):
    model_admin = get_model_admin_for_model(model_opts.model)
        
    inline_models = [
        getattr(inline, 'verbose_model', inline.model)._meta.model_name
        for inline in model_admin.inlines
        if getattr(inline, 'verbose_model', inline.model)
    ]
    
    if 'genre' in inline_models or 'schlagwort' in inline_models:# model_admin.uses_favorites(): #TODO: implement uses_favorites
        try:
            url = reverse('favoriten')
        except exceptions.NoReverseMatch:
            return ''
        return make_simple_link(url = url, label = 'Favoriten', is_popup = is_popup, as_listitem = True)
    return ''
        
from DBentry.help.templatetags import help_link
register.simple_tag(takes_context = True)(help_link)
        
        
        
        
        
        
        
        
