# views for the django default handlers
from django import http
from django.template import TemplateDoesNotExist, loader
from django.template.response import TemplateResponse

from DBentry.sites import miz_site


def MIZ_permission_denied_view(request, exception, template_name='admin/403.html'):
    # Make sure that a template for template_name exists.
    try:
        loader.get_template(template_name)
    except TemplateDoesNotExist:
        return http.HttpResponseForbidden(
            '<h1>403 Forbidden</h1>', content_type='text/html')

    msg = 'Sie haben nicht die erforderliche Berechtigung diese Seite zu sehen.'
    context = {'exception': str(exception) if str(exception) else msg}
    context.update(miz_site.each_context(request))
    context['is_popup'] = '_popup' in request.GET
    return TemplateResponse(request, template_name, context=context)
