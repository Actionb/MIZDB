from collections import OrderedDict

from django.conf import settings
from django.contrib import admin
from django.core import checks
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.views.decorators.cache import never_cache

from dbentry import utils


class MIZAdminSite(admin.AdminSite):
    site_header = 'MIZDB'
    site_title = 'MIZDB'
    
    # Do not display the “View on site” link in the header:
    site_url = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = []

    def each_context(self, request):
        context = super().each_context(request)
        # Add the URL to the wiki for the link in the header:
        if getattr(settings, 'WIKI_URL', False):
            context['wiki_url'] = settings.WIKI_URL
        return context

    def register_tool(self, view, url_name, index_label, superuser_only):
        """
        Add the given view to the sites' registered tools.

        A registered view will have a link (labelled according to 'index_label')
        to it from the index page. The view must be reversible using 'url_name'.
        If superuser_only is True, the link will only be added for superusers.
        See MIZAdminSite.index for more details.
        """
        self.tools.append((view, url_name, index_label, superuser_only))

    def check(self, app_configs):
        errors = super().check(app_configs)
        for tool, url_name, _index_label, _superuser_only in self.tools:
            try:
                reverse(url_name)
            except NoReverseMatch as e:
                errors.append(checks.Error(
                    str(e),
                    hint="Check register_tool decorator args of %s" % tool,
                    obj="%s admin tools" % self.__class__
                ))
        return errors

    def app_index(self, request, app_label, extra_context=None):
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

    def build_admintools_context(self, request):
        """
        Return a mapping of url_name: index_label of registered tools
        (ordered by index_label) to be added to the index' context.
        """
        result = OrderedDict()
        # Walk through the tools by index_label:
        tools = sorted(self.tools, key=lambda t: t[2])
        for _tool, url_name, index_label, superuser_only in tools:
            if superuser_only and not request.user.is_superuser:
                continue
            result[url_name] = index_label
        return result

    def add_categories(self, app_list):
        """Regroup the models in app_list by introducing categories."""
        # Find the index of the dbentry app:
        index = None
        try:
            index = next(
                i
                for i, d in enumerate(app_list)
                if d['app_label'] == 'dbentry'
            )
        except StopIteration:
            pass
        if index is None:
            # No app with label 'dbentry' found.
            # Return an empty app_list.
            return []

        # Get the dict containing data for the dbentry app with keys:
        # {app_url, name, has_module_perms, models, app_label}
        dbentry_dict = app_list.pop(index)
        model_list = dbentry_dict.pop('models')
        categories = OrderedDict()
        categories['Archivgut'] = []
        categories['Stammdaten'] = []
        categories['Sonstige'] = []

        # Divide the models into their categories.
        for m in model_list:
            model_admin = utils.get_model_admin_for_model(
                m['object_name'], self)
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

    @never_cache
    def index(self, request, extra_context=None):
        """
        Add the registered admintools to the index page and introduce
        grouping categories into the index' model list.
        """
        extra_context = extra_context or {}
        extra_context['admintools'] = self.build_admintools_context(request)
        response = super().index(request, extra_context)
        # Replace the original app_list with the one containing the grouping.
        new_app_list = self.add_categories(response.context_data['app_list'])
        if new_app_list:
            response.context_data['app_list'] = new_app_list
        return response

miz_site = MIZAdminSite()


class register_tool(object):
    """
    Decorator that registers a View with a given admin site.

    Required arguments:
        url_name (str): name of the URL pattern to the view.
        index_label (str): the label for the link on the index page to the view.
    Optional arguments:
        superuser_only (bool): determines whether a link to the view is displayed
                on the index page. If True, only superusers will see a link.
                This does not restrict access to the view in any way.
                Defaults to False.
        site (admin site instance): the site to register the view with.
            Defaults to 'miz_site'.
    """

    def __init__(self, url_name, index_label, superuser_only=False, site=miz_site):
        self.url_name = url_name
        self.index_label = index_label
        self.superuser_only = superuser_only
        self.site = site

    def __call__(self, tool_view):
        self.site.register_tool(
            tool_view, self.url_name, self.index_label, self.superuser_only
        )
        return tool_view
