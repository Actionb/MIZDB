from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist
from django.template.response import TemplateResponse

from dbentry.admin.site import miz_site


# TODO: remove MIZ_permission_denied_view: not used anymore since
#  5cc2d7 (site-app) added another view for 403
# noinspection PyPep8Naming
def MIZ_permission_denied_view(
    request: HttpRequest, exception: Exception, template_name: str = "admin/403.html"
) -> HttpResponse:
    """Return the permission denied template response for the MIZ site."""
    try:
        loader.get_template(template_name)
    except TemplateDoesNotExist:
        return HttpResponseForbidden("<h1>403 Forbidden</h1>", content_type="text/html")

    msg = "Sie haben nicht die erforderliche Berechtigung diese Seite zu sehen."
    context = {"exception": str(exception) if str(exception) else msg}
    context.update(miz_site.each_context(request))
    context["is_popup"] = "_popup" in request.GET  # type: ignore[assignment]
    return TemplateResponse(request, template_name, context=context)
