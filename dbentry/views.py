from django import http, views
from django.apps import apps
from django.template import TemplateDoesNotExist, loader
from django.template.response import TemplateResponse

from dbentry import utils
from dbentry.base.views import MIZAdminMixin
from dbentry.sites import miz_site, register_tool


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


@register_tool(
    url_name='site_search',
    index_label='Datenbank durchsuchen',
    superuser_only=False
)
class SiteSearchView(MIZAdminMixin, views.generic.TemplateView):
    """
    A view enabling looking up a search term on every registered non-m2m model.
    """

    app_label = 'dbentry'
    template_name = 'admin/site_search.html'
    title = 'Datenbank durchsuchen'
    breadcrumbs_title = 'Suchen'

    def get(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        q = request.GET.get('q', '')
        if q:
            context['q'] = q
            context['results'] = self.get_result_list(q)
        return self.render_to_response(context)

    def get_result_list(self, q):
        """
        Perform the queries for the search term.

        Returns a list of hyperlinks to the changelists containing the results,
        sorted by the model's object name.
        """
        from dbentry.base.models import BaseModel, BaseM2MModel  # avoid circular imports
        models = [
            m for m in apps.get_models(self.app_label)
            if issubclass(m, BaseModel) and not issubclass(m, BaseM2MModel)
        ]
        results = []
        for model in sorted(models, key=lambda m: m._meta.object_name):
            model_results = model.objects.find(q, use_separator=False)
            if not model_results:
                continue
            label = "%s (%s)" % (model._meta.verbose_name_plural, len(model_results))
            url = utils.get_changelist_url(model, self.request.user)
            if url:
                url += "?id__in=" + ",".join((str(tpl[0]) for tpl in model_results))
                results.append(utils.create_hyperlink(url, label, target="_blank"))
        return results
