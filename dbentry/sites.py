from collections import OrderedDict
from typing import Any, List, Optional, OrderedDict as OrderedDictType

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from dbentry.tools.sites import IndexToolsSite
from dbentry.utils.admin import get_model_admin_for_model


class MIZAdminSite(IndexToolsSite):
    """
    AdminSite for the dbentry app.

    It rebuilds the index page to group models into categories. The index also
    includes links to 'tool views'.
    MIZAdminSite adds a link to the site's wiki instance to the context of
    every page.
    """
    site_header = 'MIZDB'
    site_title = 'MIZDB'
    index_title = 'Index'

    # Do not display the “View on site” link in the header:
    site_url = None
    # Disable the nav sidebar:
    enable_nav_sidebar = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tools: List[tuple] = []

    def each_context(self, request: HttpRequest) -> dict:
        context = super().each_context(request)
        # Add the URL to the wiki for the link in the header:
        if getattr(settings, 'WIKI_URL', False):
            context['wiki_url'] = settings.WIKI_URL
        return context

    def app_index(
            self,
            request: HttpRequest,
            app_label: str,
            extra_context: Optional[dict] = None
    ) -> HttpResponse:
        """
        The categories added to the index page of 'dbentry' are essentially
        'fake' apps and since admin.AdminSite.app_index() is the index for a
        specific app (and thus would not include other apps), a request for the
        app_index of 'dbentry' must be redirected to index() (which collects
        all apps, including our fake ones) for the response to include the
        grouping categories.
        """
        if app_label == 'dbentry':
            # Redirect to the 'tidied' up index page of the main page
            return self.index(request, extra_context)
        return super().app_index(request, app_label, extra_context)

    def add_categories(self, app_list: List[dict]) -> List[dict]:
        """Regroup the models in app_list by introducing categories."""
        # Get the dict containing data for the dbentry app.
        # (dict keys: app_url, name, has_module_perms, models, app_label)
        dbentry_dict = None
        for i, app_dict in enumerate(app_list):
            if app_dict['app_label'] == 'dbentry':
                dbentry_dict = app_list.pop(i)
                break
        if dbentry_dict is None:
            # No app with label 'dbentry' found.
            # Return an empty app_list.
            return []

        model_list = dbentry_dict.pop('models')
        categories: OrderedDictType[str, list] = OrderedDict()
        categories['Archivgut'] = []
        categories['Stammdaten'] = []
        categories['Sonstige'] = []

        # Divide the models into their categories.
        for m in model_list:
            model_admin = get_model_admin_for_model(m['object_name'], self)
            if model_admin is None:  # pragma: no cover
                continue
            # FIXME: Add a issubclass check: only MIZModelAdmins have the
            #  get_index_category method
            # noinspection PyUnresolvedReferences
            model_category = model_admin.get_index_category()
            if model_category not in categories:
                categories['Sonstige'] = [m]
            else:
                categories[model_category].append(m)

        # Rebuild the app_list with the new categories.
        for category, models in categories.items():
            new_fake_app = dbentry_dict.copy()
            new_fake_app['name'] = category
            new_fake_app['models'] = models
            app_list.append(new_fake_app)
        return app_list

    @method_decorator(never_cache)
    def index(self, request: HttpRequest, extra_context: Optional[dict] = None) -> HttpResponse:
        response = super().index(request, extra_context)
        # Replace the original app_list with the one containing the grouping.
        new_app_list = self.add_categories(response.context_data['app_list'])
        if new_app_list:
            response.context_data['app_list'] = new_app_list
        return response


miz_site = MIZAdminSite()
