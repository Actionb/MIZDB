
from django.views.generic import TemplateView
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch


from django.utils.html import format_html

from DBentry.base.views import MIZAdminMixin
from DBentry.sites import register_tool
from DBentry.utils import has_admin_permission

@register_tool(url_name='help_index', index_label='Hilfe')
class HelpIndexView(MIZAdminMixin, TemplateView):
    """
    The view displaying an index over all available helptexts.
    Attributes:
        - registry: the registry of helptexts available to this view instance
            set during initialization by the url resolver (see help.registry.get_urls)
    """

    template_name = 'admin/help_index.html'
    site_title = breadcrumbs_title = 'Hilfe'

    registry = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if context.get('is_popup', False):
            html_template = '<a href="{url}?_popup=1">{label}</a>'
        else:
            html_template = '<a href="{url}">{label}</a>'

        # ModelAdmin Helptexts
        registered_models = []
        for model_admin in self.registry.get_registered_modeladmins():
            if not ModelAdminHelpView.permission_test(self.request, model_admin):
                continue
            model_help, url_name = self.registry._registry[model_admin]
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                continue
            registered_models.append((
                url,
                model_help(self.request, self.registry, model_admin).index_title
            ))

        # Sort by model_help.index_title // model._meta.verbose_name_plural
        model_helps = []
        for url, label in sorted(registered_models, key=lambda tpl: tpl[1]):
            model_helps.append(format_html(
                html_template,
                url=url,
                label=label
            ))
        context['model_helps'] = model_helps

        # Form Helptexts
        registered_forms = []
        for formview_class in self.registry.get_registered_forms():
            if not FormHelpView.permission_test(self.request, formview_class):
                continue
            form_help, url_name = self.registry._registry[formview_class]
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                continue

            registered_forms.append((
                url,
                form_help().index_title
            ))

        form_helps = []
        # Sort by form_help.index_title // str(form_help.form_class)
        for url, label in sorted(registered_forms, key=lambda tpl: tpl[1]):
            form_helps.append(format_html(
                html_template,
                url=url,
                label=label,
            ))
        context['form_helps'] = form_helps

        return context
# TODO: BaseHelpView should (since MIZAdminPermissionMixin was removed)
# inherit from PermissionRequiredMixin to reenable permission checking
# test_func and permission_test are essentially dead code right now
class BaseHelpView(MIZAdminMixin, TemplateView):
    """
    The base class for the HelpViews
    Attributes:
        - template_name: inherited from TemplateView
        - helptext_class: the helptext class this view is going to serve
    """

    template_name = 'admin/help.html'
    helptext_class = None


    def get_help_text(self, **kwargs):
        """
        Returns the HelpText instance (not wrapped) for this view.
        """
        if self.helptext_class is None:
            raise Exception("You must set a helptext class.")
        return self.helptext_class(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # for_context() wraps the helptext into a helper object that includes
        # the methods html() and sidenav(), which are expected by the template
        context.update(self.get_help_text().for_context())
        return context

class FormHelpView(BaseHelpView):
    """
    The view for displaying help texts for a particular form.

    Attributes:
        - target_view_class: the view that contains the form
    """

    target_view_class = None

    @staticmethod
    def permission_test(request, target_view_class):
        return True # NOTE: perrmission checking disabled, see TODO on BaseHelpView
        if issubclass(target_view_class, MIZAdminPermissionMixin): #TODO: issubclass(UserPassesTestMixin)
            # If the target_view_class has access restrictions, only allow access to its help page if the user fulfills these restrictions
            return target_view_class.permission_test(request)
        return True

    def test_func(self):
        return self.permission_test(self.request, self.target_view_class)

class ModelAdminHelpView(BaseHelpView):
    """
    The view for displaying help texts for a model admin.
    The model admin is provided as initkwarg by the url resolver.

    Attributes:
        - model_admin: set by help.registry.HelpRegistry.get_urls
        - registry: the registry of helptexts available to this view instance
            set during initialization by the url resolver (see help.registry.get_urls)
    """

    template_name = 'admin/help.html'

    model_admin = None

    registry = None

    def get_help_text(self, **kwargs):
        # Make sure the helptext gets initialized with a model_admin and a request kwarg
        if 'registry' not in kwargs:
            kwargs['registry'] = self.registry
        if 'model_admin' not in kwargs:
            kwargs['model_admin'] = self.model_admin
        if 'request' not in kwargs:
            kwargs['request'] = self.request
        return super().get_help_text(**kwargs)

    @staticmethod
    def permission_test(request, model_admin):
        return True # NOTE: perrmission checking disabled, see TODO on BaseHelpView
        # calls utils.has_admin_permission
        return has_admin_permission(request, model_admin)

    def test_func(self):
        return self.permission_test(self.request, self.model_admin)
