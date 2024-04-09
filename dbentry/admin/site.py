from collections import OrderedDict
from typing import Any, List, Optional, OrderedDict as OrderedDictType, Sequence, ValuesView

from django.conf import settings
from django.contrib import admin
from django.core import checks
from django.http import HttpRequest, HttpResponse
from django.urls import reverse, NoReverseMatch, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from dbentry.utils.admin import get_model_admin_for_model


class MIZAdminSite(admin.AdminSite):
    """
    AdminSite for the dbentry app.

    It rebuilds the index page to group models into categories. The index also
    includes links to 'tool views'.
    MIZAdminSite adds a link to the site's wiki instance to the context of
    every page.

    Also, links to registered tool views are added to the sidebar of the index
    page.
    """
    site_header = 'MIZDB'
    site_title = 'MIZDB'
    index_title = 'Index'
    # TODO: move tools/index.html stuff into the base admin index.html
    index_template = 'tools/index.html'

    site_url = reverse_lazy("index")
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
        # Add the registered admintools to the index page.
        extra_context = extra_context or {}
        extra_context['admintools'] = self.build_admintools_context(request)
        response = super().index(request, extra_context)
        # Replace the original app_list with the one containing the grouping.
        new_app_list = self.add_categories(response.context_data['app_list'])
        if new_app_list:
            response.context_data['app_list'] = new_app_list
        return response

    def check(self, app_configs: Optional[ValuesView]) -> List[checks.CheckMessage]:
        errors = super().check(app_configs)
        # Check that the registered urls are reversible.
        for tool, url_name, *_ in self.tools:
            try:
                reverse(url_name)
            except NoReverseMatch as e:
                errors.append(
                    checks.Error(
                        str(e),
                        hint="Check register_tool decorator args of %s" % tool,
                        obj="%s admin tools" % self.__class__
                    )
                )
        return errors

    def register_tool(
            self,
            view: View,
            url_name: str,
            index_label: str,
            permission_required: Sequence = (),
            superuser_only: bool = False
    ) -> None:
        """
        Add the given view to the sites' registered tools. A link to the
        registered view will be displayed in the sidebar of the index page.

        Args:
            view: the tool view
            url_name: the reversible url name of the view
            index_label: the label for the link
            permission_required: permissions required for the link to be
              displayed on the index page
            superuser_only: if True, a link will only be displayed to superusers
        """
        self.tools.append((view, url_name, index_label, permission_required, superuser_only))

    def build_admintools_context(self, request: HttpRequest) -> OrderedDictType[str, str]:
        """
        Return a mapping of url_name: index_label of registered tools, ordered
        by index_label, to be added to the index's context.
        Exclude tool views the user does not have permission for.
        """
        result = OrderedDict()
        # noinspection PyUnresolvedReferences
        user = request.user
        # Walk through the tools sorted by index_label:
        for _tool, url, label, perms, su_only in sorted(self.tools, key=lambda tpl: tpl[2]):
            if su_only and not user.is_superuser:
                continue
            if not user.has_perms(perms):
                continue
            result[url] = label
        return result


miz_site = MIZAdminSite()
