from django.template import Library
from django.utils.html import format_html
from django.contrib.admin.views.main import ORDER_VAR

register = Library()

@register.simple_tag
def reset_ordering(cl):
    template = '<span class="small quiet"><a href={url}>Sortierung zurücksetzen</a></span>'
    url = cl.get_query_string(new_params = None, remove = [ORDER_VAR])
    return format_html(template, url = url)
    
