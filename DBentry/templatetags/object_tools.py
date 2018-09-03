
from django.urls import reverse, exceptions
from django.utils.html import format_html, mark_safe
from django.template import Library

from DBentry.utils import get_model_admin_for_model


register = Library()

@register.simple_tag
def object_tools(model_opts, is_popup = False):
    from DBentry.help.registry import halp
    
    model_admin = get_model_admin_for_model(model_opts.model)
    
    help_link = favorites_link = ''
    if is_popup:
        html_template = '<li><a href="{url}{popup}" onclick="{target_or_onclick}">{label}</a></li>'
    else:
        html_template = '<li><a href="{url}{popup}" target="{target_or_onclick}">{label}</a></li>'
    
    if halp.is_registered(model_opts.model):
        try:
            help_link = format_html(
                html_template, 
                url = reverse('help', kwargs = {'model_name': model_opts.model_name}), 
                popup = '?_popup=1' if is_popup else '', 
                label = 'Hilfe',
                target_or_onclick = 'return popup(this)' if is_popup else '_blank'
            )
        except exceptions.NoReverseMatch:
            pass
    inline_models = [
        getattr(inline, 'verbose_model', inline.model)._meta.model_name
        for inline in model_admin.inlines
        if getattr(inline, 'verbose_model', inline.model)
    ]
    if 'genre' in inline_models or 'schlagwort' in inline_models:# model_admin.uses_favorites(): #TODO: implement uses_favorites
        try:
            favorites_link = format_html(
                html_template, 
                url = reverse('favoriten'), 
                popup = '?_popup=1' if is_popup else '', 
                label = 'Favoriten', 
                target_or_onclick = 'return popup(this)' if is_popup else '_blank'
            )
        except exceptions.NoReverseMatch:
            pass
    return mark_safe(help_link + favorites_link)
