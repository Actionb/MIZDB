
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
    
    url_name = ''
    reverse_args = ()
    reverse_kwargs = {}

    if not hasattr(request.resolver_match.func, 'model_admin'):
        # This is not a ModelAdmin view, it's a 'custom' view; get this view's helptext #TODO: THEN WHY ARE WE LOOKING FOR A FORM AND NOT A VIEW?!
        form_class = request.resolver_match.func.view_class.form_class
        for _url_name, form_helptext in halp.get_registered_forms().items():
            if form_helptext.form_class == form_class:
                url_name = _url_name
                break
    else:
        # This is a ModelAdmin view for the add/change page of a certain model
        model = request.resolver_match.func.model_admin.model
        if halp.is_registered(model):
            url_name = 'help'
            reverse_kwargs = {'model_name': model._meta.model_name}
    if url_name:
        try:
            return format_html(
                _get_default_template(is_popup), 
                url = reverse(url_name, args = reverse_args, kwargs = reverse_kwargs), 
                label = 'Hilfe', 
            )
        except exceptions.NoReverseMatch:
            pass
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
        
        
        
        
        
        
        
        
        
        
