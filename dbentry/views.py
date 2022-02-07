import datetime
from typing import Any, List, Tuple, Type

from django import forms, views
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist
from django.template.response import TemplateResponse
from django.utils.safestring import SafeText
from django.utils.timezone import now

from dbentry import models, utils
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

    def get(self, request: HttpRequest, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data(**kwargs)
        q = request.GET.get('q', '')
        if q:
            context['q'] = q
            context['results'] = self.get_result_list(q)
        return self.render_to_response(context)

    def get_result_list(self, q: str) -> List[SafeText]:
        """
        Perform the queries for the search term ``q``.

        Returns:
            a list of hyperlinks to the changelists containing the results,
             sorted by the model's object name
        """
        from dbentry.base.models import BaseModel, BaseM2MModel  # avoid circular imports
        models = [
            m for m in apps.get_models(self.app_label)
            if issubclass(m, BaseModel) and not issubclass(m, BaseM2MModel)
        ]
        results = []
        # noinspection PyProtectedMember
        for model in sorted(models, key=lambda m: m._meta.object_name):
            model_results = model.objects.search(q, ranked=False)
            if not model_results:
                continue
            # noinspection PyProtectedMember
            label = "%s (%s)" % (model._meta.verbose_name_plural, len(model_results))
            url = utils.get_changelist_url(model, self.request.user)
            if url:
                url += f"?q={q!s}"
                results.append(utils.create_hyperlink(url, label, target="_blank"))
        return results


def watchlist_toggle(request, *args, **kwargs):
    """
    Add or remove an object from the watchlist.

    Clicking on the 'Watchlist' checkbox element in the object tools section of
    a change form prompts an AJAX request to this view.
    """
    # TODO: mention remove_only in the docstring
    # TODO: mention using either model for authenticated and session for anonymous
    # TODO: mention that the session watchlist is (pk, time_added)
    pk = int(request.GET['id'])
    model_label = request.GET['model_label']

    # Only try removing the item
    # Scenario:
    #   - item x on watchlist
    #   - user is on the watchlist overview AND the item's change page
    #   - user hits 'watchlist' checkbox on the CHANGE PAGE
    #   - item gets removed from watchlist
    #   - user hits checkbox on the watchlist overview (no async refresh)
    #   - item must not be added again
    remove_only = request.GET.get('remove_only', False)  # TODO: should be POST as we create model instances

    # Check that the model exists, and that a model instance with that primary
    # key can be found.
    try:
        model = apps.get_model(model_label)
        try:
            obj = model.objects.get(pk=pk)
        except model.DoesNotExist:
            return JsonResponse({'on_watchlist': False})
    except LookupError:
        return JsonResponse({'on_watchlist': False})

    if request.user.is_authenticated:
        content_type = ContentType.objects.get_for_model(model)
        watchlist = models.Watchlist.objects.filter(
            user=request.user, content_type=content_type, object_id=pk
        )
        if remove_only or watchlist.exists():
            watchlist.delete()
            on_watchlist = False
        else:
            watchlist.create(
                user=request.user,
                content_type=content_type,
                object_id=pk,
                object_repr=repr(obj)
            )
            on_watchlist = True
    else:
        if 'watchlist' not in request.session:
            request.session['watchlist'] = {}
        watchlist = request.session['watchlist']

        if remove_only or (model_label in watchlist and pk in watchlist[model_label]):
            try:
                watchlist[model_label].remove(pk)
            except (KeyError, ValueError):
                # remove_only is True, and the item wasn't on the watchlist
                pass
            on_watchlist = False
        else:
            if model_label not in watchlist:
                watchlist[model_label] = [(pk, now())]
            else:
                watchlist[model_label].append((pk, now()))
            on_watchlist = True
        # Must flag the session object as modified to save the watchlist.
        request.session.modified = True
    return JsonResponse({'on_watchlist': on_watchlist})


def get_watchlist(request):
    """Return the watchlist for the given request."""
    if request.user.is_authenticated:
        watchlist = {}
        for watchlist_item in models.Watchlist.objects.filter(user=request.user):
            model_label = watchlist_item.content_type.model_class()._meta.label
            if model_label not in watchlist:
                watchlist[model_label] = []
            watchlist[model_label].append((
                watchlist_item.object_id, watchlist_item.added
            ))
        return watchlist
    # TODO: session items won't be ordered by time_added / 'added'
    #   <-- wouldn't they? the items are appended
    return request.session.get('watchlist', {})


@register_tool(
    url_name='watchlist',
    index_label='Merkliste',
    superuser_only=False
)
class Watchlist(MIZAdminMixin, views.generic.TemplateView):
    template_name = 'admin/watchlist.html'

    def get_headers(self, model):
        """Get the headers for the watchlist table for the given model."""
        ...

    def get_item_bestand(self, obj):
        """Get the Bestand for the given model instance."""
        items = []
        if isinstance(obj, models.Artikel):
            items = obj.ausgabe.bestand_set.all()
        elif hasattr(obj, 'bestand_set'):
            items = obj.bestand_set.all()
        return ", ".join(str(b) for b in items)

    def get_item_extra(self, obj):
        """Get the data to display for the given model instance."""
        if isinstance(obj, models.Artikel):
            return (
                ('Seite', f"{obj.seite}{obj.seitenumfang}"),
                ('Magazin', obj.ausgabe.magazin.magazin_name),
                ('Ausgabe', str(obj.ausgabe))
            )
        return ()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        watchlist = get_watchlist(self.request)
        context['watchlist'] = []
        for model_label in sorted(watchlist.keys()):
            model = apps.get_model(model_label)
            items: List[Tuple[int, SafeText, Tuple, str, datetime.datetime]] = []
            extra_headers: List[str] = []
            objects: List['Type[Model]'] = []
            for pk, added in watchlist[model_label]:
                # TODO: get() could return no/multiple objects
                #  (id might have become invalid -> deleted object)
                #  use pre_delete signal to remove items from watchlist?
                obj = model.objects.get(pk=pk)
                objects.append(obj)
                link = utils.get_obj_link(obj, self.request.user)
                extra = self.get_item_extra(obj)
                if extra:
                    extra_headers, extra_data = zip(*self.get_item_extra(obj))
                else:
                    extra_data = []
                bestand = self.get_item_bestand(obj)
                # object_id, change page, bestand list, time added
                items.append((pk, link, extra_data, bestand, added))  # TODO: localize 'added'
            if items:
                # Add a link to the changelist page of this group.
                cl_url = utils.get_changelist_url(
                    model, self.request.user, obj_list=objects
                )
                cl_link = utils.create_hyperlink(
                    url=cl_url, content='Änderungsliste',
                    **{'target': '_blank', 'class': 'button cl-button'}
                )
                # model_opts, headers, items, cl_link
                context['watchlist'].append((model._meta, extra_headers, items, cl_link))

        extra = '' if settings.DEBUG else '.min'
        js = [
            'vendor/jquery/jquery%s.js' % extra,
            'jquery.init.js',
            'watchlist.js'
        ]
        context['media'] = forms.Media(
            js=['admin/js/%s' % url for url in js],
            css={'all': ['admin/css/widgets.css']}
        )
        return context
