from itertools import chain

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from dbentry.fts.query import TextSearchQuerySetMixin
from dbentry.site.registry import miz_site
from dbentry.utils import get_obj_link, create_hyperlink
from dbentry.utils.url import get_changelist_url


class SearchbarSearch(View):
    blank = False

    # TODO: add variable that dictates whether to include target="_blank" in the links
    #  (blank if in a add/change form)

    def get(self, request, **kwargs):
        # TODO: stagger the searches? Search important models first and return
        #  those results before searching less important ones?
        data = {'results': [], 'total_count': 0}
        if q := request.GET.get('q', ''):
            for queryset in self.get_results(q):
                data['total_count'] += queryset.count()
                data['results'].append({
                    'category': self.get_changelist_link(queryset),
                    'items': [
                        get_obj_link(obj, self.request.user, site_name=settings.SITE_NAMESPACE, blank=self.blank)
                        for obj in queryset
                    ]
                })
        return JsonResponse(data)

    def get_results(self, q):
        results = []
        for model in self.get_models():
            queryset = model.objects.all()
            if isinstance(queryset, TextSearchQuerySetMixin):
                model_results = queryset.search(q, ranked=False)
            elif name_field := getattr(model, 'name_field', None):
                model_results = queryset.filter(**{name_field + '__icontains': q})
            else:
                continue  # pragma: no cover https://github.com/nedbat/coveragepy/issues/198#issuecomment-399705984
            if model_results.exists():
                results.append(model_results)
        return results

    def get_models(self):
        """Hook for specifying which models to query."""
        return set(chain(miz_site.views.keys(), miz_site.changelists.keys()))

    def get_changelist_link(self, queryset):
        opts = queryset.query.get_meta()
        url = get_changelist_url(
            queryset.query.model,
            self.request.user,
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
