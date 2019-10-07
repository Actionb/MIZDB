from collections import OrderedDict

from django.apps import apps
from django.contrib import admin
from django.views.decorators.cache import never_cache


class MIZAdminSite(admin.AdminSite):
    site_header = 'MIZDB'
    site_title = 'MIZDB'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = []

    def register_tool(self, view, url_name, index_label, superuser_only):
        """
        Add the given view to the sites' registered tools.

        A registered view will have a link (labelled according to 'index_label')
        to it from the index page. The view must be reversible using 'url_name'.
        If superuser_only is True, the link will only be added for superusers.
        See MIZAdminSite.index for more details.
        """
        self.tools.append((view, url_name, index_label, superuser_only))

    def app_index(self, request, app_label, extra_context=None):
        if app_label == 'DBentry':
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
        # Find the index of the DBentry app:
        index = None
        try:
            index = next(
                i
                for i, d in enumerate(app_list)
                if d['app_label'] == 'DBentry'
            )
        except StopIteration:
            pass
        if index is None:
            # No app with label 'DBentry' found.
            # Return an empty app_list.
            return []

        # Get the dict containing data for the DBentry app with keys:
        # {app_url, name, has_module_perms, models, app_label}
        dbentry_dict = app_list.pop(index)
        model_list = dbentry_dict.pop('models')
        categories = OrderedDict()
        categories['Archivgut'] = []
        categories['Stammdaten'] = []
        categories['Sonstige'] = []

        # Divide the models into their categories.
        for m in model_list:
            model_admin = self.get_admin_model(m.get('object_name'))
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

    def get_admin_model(self, model):
        """
        Return the ModelAdmin instance that represents the given 'model'.
        'model' can be a model class or the name of a model.
        """
        # TODO: does the same as utils.admin.get_model_admin_for_model
        if isinstance(model, str):
            model_name = model.split('.')[-1]
            try:
                model = apps.get_model('DBentry', model_name)
            except LookupError:
                return None
        return self._registry.get(model, None)


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
