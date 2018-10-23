
from django.urls import reverse, exceptions
from django.utils.html import format_html
from django.template import Library

from DBentry.utils import get_model_admin_for_model


register = Library()

def _get_default_template(is_popup):
    if is_popup:
        return '<li><a href="{url}?_popup=1" onclick="return popup(this)">{label}</a></li>'
    else:
        return '<li><a href="{url}" target="_blank">{label}</a></li>'
        
@register.simple_tag   
def help_link(request, is_popup = False):
    from DBentry.help.registry import halp

    if hasattr(request.resolver_match.func, 'model_admin'):
        # This is a ModelAdmin view for the add/change page of a certain model
        url = halp.help_url_for_view(request.resolver_match.func.model_admin)
    else:
        # This is not a ModelAdmin view, it's a 'custom' view; get the helpview's url
        url = halp.help_url_for_view(request.resolver_match.func.view_class)
        
    if url:
        return format_html(
            _get_default_template(is_popup), 
            url = url,
            label = 'Hilfe', 
        )
    return ''
    
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
            return format_html(
                _get_default_template(is_popup), 
                url = reverse('favoriten'), 
                label = 'Favoriten', 
            )
        except exceptions.NoReverseMatch:
            pass
    return ''
        
        
        
        
        
        
        
        
        
        
