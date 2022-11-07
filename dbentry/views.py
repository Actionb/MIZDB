from typing import Any, List

from django import views
from django.apps import apps
from django.db.models import Model
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist
from django.template.response import TemplateResponse
from django.utils.safestring import SafeText

from dbentry import utils
from dbentry.base.views import MIZAdminMixin
from dbentry.sites import miz_site, register_tool


# noinspection PyPep8Naming
def MIZ_permission_denied_view(
        request: HttpRequest,
        exception: Exception,
        template_name: str = 'admin/403.html'
) -> HttpResponse:
    """Return the permission denied template response for the MIZ site."""
    try:
        loader.get_template(template_name)
    except TemplateDoesNotExist:
        return HttpResponseForbidden(
            '<h1>403 Forbidden</h1>', content_type='text/html'
        )

    msg = 'Sie haben nicht die erforderliche Berechtigung diese Seite zu sehen.'
    context = {'exception': str(exception) if str(exception) else msg}
    context.update(miz_site.each_context(request))
    context['is_popup'] = '_popup' in request.GET  # type: ignore[assignment]
    return TemplateResponse(request, template_name, context=context)


class SiteSearchView(views.generic.TemplateView):
    """
    A view enabling looking up a search term on every model installed on a
    given app.
    """

    app_label = ''
    template_name = 'admin/site_search.html'

    def get(self, request: HttpRequest, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data(**kwargs)
        q = request.GET.get('q', '')
        if q:
            context['q'] = q
            context['results'] = self.get_result_list(q)
        return self.render_to_response(context)

    def _get_models(self, app_label: str = '') -> List[Model]:
        """
        Return a list of models to be queried.

        Args:
            app_label (str): name of the app whose models should be queried
        """
        app = apps.get_app_config(app_label or self.app_label)
        return app.get_models()

    def _search(self, model: Model, q: str) -> []:
        """Search the given model for the search term ``q``."""
        raise NotImplementedError("The view class must implement the search.")  # pragma: no cover

    def get_result_list(self, q: str) -> List[SafeText]:
        """
        Perform the queries for the search term ``q``.

        Returns:
            a list of hyperlinks to the changelists containing the results,
             sorted by the model's object name
        """
        results = []
        for model in sorted(self._get_models(), key=lambda m: m._meta.object_name):
            model_results = self._search(model, q)
            if not model_results:
                continue
            # noinspection PyUnresolvedReferences
            label = "%s (%s)" % (model._meta.verbose_name_plural, len(model_results))
            url = utils.get_changelist_url(model, self.request.user)
            if url:
                url += f"?q={q!s}"
                results.append(utils.create_hyperlink(url, label, target="_blank"))
        return results


@register_tool(
    url_name='site_search',
    index_label='Datenbank durchsuchen',
    superuser_only=False
)
class MIZSiteSearch(MIZAdminMixin, SiteSearchView):
    app_label = 'dbentry'

    title = 'Datenbank durchsuchen'
    breadcrumbs_title = 'Suchen'

    def _get_models(self, app_label: str = '') -> List[Model]:
        # Limit the models to those subclassing BaseModel only.
        from dbentry.base.models import BaseModel, BaseM2MModel  # avoid circular imports
        # noinspection PyTypeChecker
        return [
            m for m in super()._get_models(app_label)
            if issubclass(m, BaseModel) and not issubclass(m, BaseM2MModel)
        ]

    def _search(self, model: Model, q: str) -> []:
        # noinspection PyUnresolvedReferences
        return model.objects.search(q, ranked=False)  # pragma: no cover
