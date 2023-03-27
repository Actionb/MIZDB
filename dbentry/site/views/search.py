from django.conf import settings
from django.http import HttpResponse
from django.views import View

from dbentry import models as _models
from dbentry.utils import get_changelist_url, get_obj_link, create_hyperlink


class SearchbarSearch(View):

    max_result_models = 3
    max_model_items = 6
    blank = False
    # TODO: add variable that dictates whether to include target="_blank" in the links
    #  (blank if in a add/change form)

    def get(self, request, **kwargs):
        # TODO: return a JSONResponse and let the javascript handle the HTML instead?
        #  that way, you wouldn't have to decode the response byte string in JS
        if q := request.GET.get('q', ''):
            results = self.get_results(q)
            if results:
                return HttpResponse(content=self.get_result_html(results))
        return HttpResponse("Keine Ergebnisse")

    def get_results(self, q):
        results = []
        for model in self.models:
            model_results = model.objects.search(q, ranked=False)
            if model_results.exists():
                results.append(model_results)
        return results

    def get_result_html(self, results):
        if (len(results) < self.max_result_models
                and all(result.count() < self.max_model_items for result in results)):
            return self._detail_html(results)
        else:
            return self._list_html(results)

    def get_changelist_link(self, queryset):
        opts = queryset.query.get_meta()
        url = get_changelist_url(
            queryset.query.model,
            self.request.user,
            site_name=settings.SITE_NAMESPACE,
            obj_list=queryset,
        )
        if queryset.count() > 1:
            label = f"{opts.verbose_name_plural} ({queryset.count()})"
        else:
            label = opts.verbose_name
        if not url:
            return label
        if self.blank:
            return create_hyperlink(url, label, target='_blank')
        return create_hyperlink(url, label)

    def _detail_html(self, results):
        indent = "\t"
        lists = ""
        for queryset in results:
            items = ""
            for obj in queryset:
                link = get_obj_link(obj, self.request.user, site_name=settings.SITE_NAMESPACE, blank=self.blank)
                items += f"{indent * 2}<li>{link}</li>\n"
            sublist = f"\n{indent}<ul>\n{items}\n{indent}</ul>\n{indent}"
            lists += f"{indent}<li>{self.get_changelist_link(queryset)}{sublist}</li>"
        return f"<ul>{lists}</ul>"

    def _list_html(self, results):
        items = ""
        for queryset in results:
            items += f"<li>{self.get_changelist_link(queryset)}</li>"
        return f"<ul>{items}</ul>"

    @property
    def models(self):
        # TODO: implement this
        return [_models.Band]

        if hasattr(self, '_models'):
            return self._models




