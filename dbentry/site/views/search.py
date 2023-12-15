from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from dbentry.site.registry import miz_site
from dbentry.site.views import BaseViewMixin
from dbentry.utils.html import create_hyperlink, get_obj_link, get_view_link
from dbentry.utils.permission import has_change_permission
from dbentry.utils.url import get_changelist_url


class SearchViewMixin:
    """
    A view mixin that queries a list of models for a given search term `q`.

    By default, queries will be made against the models registered with
    `miz_site`.
    """

    def get_results(self, q):
        """Return the results for the given search term."""
        return self._get_results(q, self._get_querysets(self.get_models()))

    def _get_results(self, q, querysets):
        """
        Query each queryset in `querysets` using the given search term `q`.

        Returns a list of querysets that returned results for the search term.
        """
        results = []
        for queryset in querysets:
            result = self._get_model_results(q, queryset)
            if result.exists():
                results.append(result)
        return results

    def get_models(self):
        """Hook for specifying which models to query."""
        return [opts.model for _category, model_options in miz_site.model_list for opts in model_options]

    def _get_querysets(self, models):
        """Return the querysets for the given models."""
        return [model.objects for model in models]

    def _get_model_results(self, q, queryset):
        """Return search results for the given queryset."""
        return queryset.search(q, ranked=False)

    def get_changelist_link(self, request, queryset, q):
        """
        Return a hyperlink element that links to the changelist of the
        queryset's model. The URL's query string will contain the search term.
        """
        opts = queryset.query.get_meta()
        return self._get_changelist_link(
            url=self._get_changelist_link_url(request, opts.model, q),
            label=self._get_changelist_link_label(queryset, opts),
            popup="popup" in request.GET,
        )

    def _get_changelist_link_url(self, request, model, q):
        """
        Return the URL to the changelist of the given model, with the search
        term appended as query string parameter.

        If the user does not have view permissions, an empty string is returned
        instead.
        """
        url = get_changelist_url(request, model)
        if url:
            # Append a query string containing the search term
            url += f"?q={q}"
        return url

    def _get_changelist_link_label(self, queryset, opts):
        """Return an appropriate label for the changelist link."""
        if queryset.count() > 1:
            return f"{opts.verbose_name_plural} ({queryset.count()})"
        else:
            return opts.verbose_name

    def _get_changelist_link(self, url, label, popup):
        """Return a hyperlink element that links to the given URL."""
        if not url:
            return label
        attrs = {"class": "text-decoration-none"}
        if popup:
            attrs["target"] = "_blank"
        return create_hyperlink(url, label, **attrs)


class SearchbarSearch(SearchViewMixin, View):
    """
    This view serves as the endpoint for queries made with the searchbar.

    The JSON response will contain the total count of results across all models
    and a list of model result dictionaries.
    A model result dictionary contains:
        - `model_name`: the model name
        - `changelist_link`: a link to the model's changelist (with the search
          term included as part of the URL query string)
        - `details`: a list of links to the change pages of individual results.
          This is list is only included if there are less than 20 results for
          the model.
    """

    def _get_changelist_link_label(self, queryset, opts):
        return super()._get_changelist_link_label(queryset, opts).upper()

    def get(self, request, **kwargs):
        data = {"results": [], "total_count": 0}
        if q := request.GET.get("q", ""):
            for queryset in self.get_results(q):
                opts = queryset.query.get_meta()
                data["total_count"] += queryset.count()
                model_results = {
                    "model_name": opts.model_name,
                    "changelist_link": self.get_changelist_link(request, queryset, q),
                }
                if queryset.count() < 20:
                    link_func = get_view_link
                    if has_change_permission(request.user, opts):
                        link_func = get_obj_link
                    model_results["details"] = [
                        link_func(request, obj, blank="popup" in request.GET) for obj in queryset
                    ]
                data["results"].append(model_results)
        return JsonResponse(data)


class SiteSearchView(SearchViewMixin, BaseViewMixin, TemplateView):
    """Dedicated results page for the full text search."""

    template_name = "mizdb/site_search.html"
    title = "Datenbank durchsuchen"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        results = []
        total_count = 0
        if q := self.request.GET.get("q", ""):
            ctx["q"] = q
            for queryset in self.get_results(q):
                total_count += queryset.count()
                results.append(self.get_changelist_link(self.request, queryset, q))
        ctx["results"] = results
        ctx["total_count"] = total_count
        return ctx
