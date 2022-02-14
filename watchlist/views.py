from operator import itemgetter

from django import views
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.forms import forms
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.timezone import now

from dbentry import utils
from watchlist.models import Watchlist


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
        watchlist = Watchlist.objects.filter(
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
        if 'watchlist' not in request.session:  # pragma: no cover
            request.session['watchlist'] = {}
        watchlist = request.session['watchlist']
        pks = list(map(itemgetter(0), watchlist.get(model_label, [])))

        if remove_only or model_label in watchlist and pk in pks:
            try:
                watchlist[model_label].pop(pks.index(pk))
            except (KeyError, ValueError):
                # remove_only is True, and the item wasn't on the watchlist
                pass
            on_watchlist = False
        else:
            if model_label not in watchlist:  # pragma: no cover
                watchlist[model_label] = [(pk, now())]
            else:
                watchlist[model_label].append((pk, now()))
            on_watchlist = True
        # Must flag the session object as modified to save the watchlist.
        request.session.modified = True
    return JsonResponse({'on_watchlist': on_watchlist})


def get_watchlist(request) -> dict[str, list]:
    """
    Return the watchlist of the current user.

    If the user is authenticated, check the Watchlist model. Otherwise, use the
    watchlist stored in the session.

    Returns:
        a dictionary that maps model labels to lists of 2-tuples containing
         object id and time added (to the watchlist) for each watchlist item
    """
    if not request.user.is_authenticated:
        return request.session.get('watchlist', {})

    watchlist = {}
    # noinspection PyUnresolvedReferences
    for watchlist_item in Watchlist.objects.filter(user=request.user):
        # Use all lower case for the model label to make the string consistent
        # with labels sent to watchlist_toggle by AJAX requests that use all
        # lower case.
        # noinspection PyProtectedMember
        model_label = watchlist_item.content_type.model_class()._meta.label.lower()
        if model_label not in watchlist:  # pragma: no cover
            watchlist[model_label] = []
        watchlist[model_label].append((
            watchlist_item.object_id, watchlist_item.added
        ))
    return watchlist


def watchlist_changelist(request, app_label, model_name):
    """
    Redirect to the changelist of the requested model, filtered to items on the
    watchlist.
    """
    x = request.GET
    # model_label = request.GET['model_label']
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        # TODO: send admin message with level ERROR
        # TODO: redirect back to watchlist?
        redirect('index')

    cl_url = utils.get_changelist_url(model, request.user)
    try:
        model_watchlist = get_watchlist(request)[f"{app_label}.{model_name}"]
        pks = ','.join(str(pk) for pk in map(itemgetter(0), model_watchlist))
        return redirect(f"{cl_url}?id__in={pks}")
    except KeyError:
        return redirect(cl_url)


class WatchlistView(views.generic.TemplateView):

    template_name = 'admin/watchlist.html'

    def get_item_extra(self, obj: Model) -> list[tuple[str, str]]:
        """
        Get additional data to display for the given model instance.

        Returns:
            a sequence of two-tuples containing the label for the table header
              and the string representation of the data to be displayed
        """
        return []

    def get_watchlist_context(self, request):
        watchlist = get_watchlist(request)
        context_items = []
        for model_label in sorted(watchlist.keys()):
            model = apps.get_model(model_label)
            extra_headers = []
            objects = []

            # For each model object, provide the template with the following:
            #   - the object's primary key value
            #   - clickable link to the change page of that object
            #   - additional data to be displayed in the listing/table
            #   - timestamp of when the object was added to the watchlist
            items = []
            for pk, added in watchlist[model_label]:
                # TODO: get() could return no/multiple objects
                #  (id might have become invalid -> deleted object)
                #  use pre_delete signal to remove items from watchlist?
                obj = model.objects.get(pk=pk)  # FIXME: this requires a query for every watchlist item
                objects.append(obj)
                link = utils.get_obj_link(obj, self.request.user)
                extra = self.get_item_extra(obj)
                if extra:
                    extra_headers, extra_data = zip(*self.get_item_extra(obj))
                else:
                    extra_data = []
                # TODO: localize datetime value for 'added'
                items.append((pk, link, extra_data, added))

            if items:
                # Add a link to the changelist page of this group.
                cl_url = utils.get_changelist_url(
                    model, self.request.user, obj_list=objects
                )
                cl_link = utils.create_hyperlink(
                    url=cl_url, content='Änderungsliste',
                    **{'target': '_blank', 'class': 'button cl-button'}
                )
                # noinspection PyProtectedMember
                context_items.append((model._meta, extra_headers, items, cl_link))
        return context_items

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['watchlist'] = self.get_watchlist_context(self.request)
        extra = '' if settings.DEBUG else '.min'
        # TODO: add watchlist.js and watchlist.css to this app's static
        js = [
            'vendor/jquery/jquery%s.js' % extra,
            'jquery.init.js',
            'watchlist.js'
        ]
        # TODO: add watchlist.css
        context['media'] = forms.Media(
            js=['admin/js/%s' % url for url in js],
            css={'all': ['admin/css/widgets.css']}
        )
        return context
