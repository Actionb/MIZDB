from DBentry.utils import make_simple_link

def help_link(context):
    from DBentry.help.registry import halp
    if 'request' in context:
        request = context['request']
    elif 'view' in context and hasattr(context['view'], 'request'):
        # Get the request through the view context item that was added by views.generic.base.ContextMixin
        request = context['view'].request
    else:
        # Cannot proceed with out the request!
        return ''
    
    if hasattr(request.resolver_match.func, 'model_admin'):
        # This is a ModelAdmin view for the add/change page of a certain model
        url = halp.help_url_for_view(request.resolver_match.func.model_admin)
    else:
        # This is not a ModelAdmin view, it's a 'custom' view; get the helpview's url
        url = halp.help_url_for_view(request.resolver_match.func.view_class)
        
    if not url:
        return ''
    return make_simple_link(url=url, label='Hilfe', is_popup=context.get('is_popup', False), as_listitem=True)
