from django import views
from django.contrib import auth
from django.contrib.auth.mixins import UserPassesTestMixin

from formtools.wizard.views import SessionWizardView

from DBentry.sites import miz_site
from DBentry.utils import get_model_from_string

PERM_DENIED_MSG = 'Sie haben nicht die erforderliche Berechtigung diese Seite zu sehen.'


class MIZAdminMixin(object):
    """
    Add admin_site specific context (each_context) to the view.
    """

    site_title = None
    breadcrumbs_title = None
    admin_site = miz_site

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        # Add admin site context.
        context.update(self.admin_site.each_context(self.request))
        # Enable popups behaviour for custom views.
        context['is_popup'] = '_popup' in self.request.GET
        if self.site_title:
            context['site_title'] = self.site_title
        if self.breadcrumbs_title: 
            context['breadcrumbs_title'] = self.breadcrumbs_title
        return context

class MIZAdminPermissionMixin(MIZAdminMixin, UserPassesTestMixin):
    #TODO: revisit MIZAdminPermissionMixin:
    #   - UserPassesTestMixin vs PermissionRequiredMixin
    #   - pass custom kwargs to test func (would be needed for class/staticmethod test_funcs with no instance access)
    """A mixin that enables permission restricted views."""

    permission_denied_message = PERM_DENIED_MSG
    raise_exception = True
    _permissions_required = []

    #@cached_property
    @classmethod
    def get_permissions_required(cls):
        permissions_required = []
        for perm_tuple in cls._permissions_required:
            model = None
            if isinstance(perm_tuple, str):
                perm_code = perm_tuple
            elif len(perm_tuple)==1:
                perm_code = perm_tuple[0]
            else:
                perm_code, model = perm_tuple
                if isinstance(model, str):
                    model = get_model_from_string(model)
            if model is None:
                if hasattr(cls, 'opts'):
                    opts = getattr(cls, 'opts')
                elif hasattr(cls, 'model'):
                    opts = getattr(cls, 'model')._meta
                else:
                    from django.core.exceptions import ImproperlyConfigured
                    raise ImproperlyConfigured("No model/opts set for permission code '{}'. ".format(perm_code)+\
                        "To explicitly set required permissions, create a list of permission codenames as an attribute named 'permissions_required'."
                        )
            else:
                opts = model._meta
            perm = '{}.{}'.format(opts.app_label, auth.get_permission_codename(perm_code, opts))
            permissions_required.append(perm)
        return permissions_required

    @classmethod
    def permission_test(cls, request):
        """
        The test function that the user has to pass for contrib.auth's UserPassesTestMixin to access the view.
        Default permission level is: is_staff
        """
        permissions_required = cls.get_permissions_required()
        if permissions_required:
            for perm in permissions_required:
                if not request.user.has_perm(perm):
                    return False
            return True
        else:
            return request.user.is_staff

    def test_func(self):
        #TODO: overwrite get_test_func() instead!
        """
        Redirect the test for UserPassesTestMixin to a more aptly named function.
        """
        return self.permission_test(self.request)


class MIZAdminToolViewMixin(MIZAdminPermissionMixin):
    """
    The base mixin for all 'Admin Tools'.

    While the mixin itself does not add much, any view must use this
    mixin to be registered as a 'tool view' (see DBentry.sites.register_tool).
    """

    @staticmethod
    def show_on_index_page(request):
        """
        Return a boolean indicating whether a link to this view should be
        displayed on the index page. If the view requires specific permissions,
        no link will be displayed if the user does not have these permissions
        even if True is returned.
        """
        return request.user.is_staff


class OptionalFormView(views.generic.FormView):
    """A FormView that does not require form_class to be set."""

    def get_form(self, form_class=None):
        if self.get_form_class() is None:
            # The form is optional.
            return None
        return super().get_form(form_class)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form is None or form.is_valid():
            # Treat an optional form like a valid form.
            return self.form_valid(form)
        else:
            # This view has a form_class set, but the form is invalid.
            return self.form_invalid(form)


class FixedSessionWizardView(SessionWizardView):
    """
    Subclass of SessionWizardView that fixes some quirks.
    """

    def get_context_data(self, form=None, **kwargs):
        # SessionWizardView expects 'form' as required positional argument.
        return super().get_context_data(form, **kwargs)

    def get_form(self, step=None, data=None, files=None): 
        """ 
        WizardView.get_form overrides any alterations to the form kwargs
        made in self.get_form_kwargs:

            kwargs = self.get_form_kwargs(step)
            kwargs.update({
                'data': data,
                'files': files,
                'prefix': self.get_form_prefix(step, form_class),
                'initial': self.get_form_initial(step),
            })
            Where 'step', 'data' and 'files' are get_form's arguments.
        """
        if step is None: 
            step = self.steps.current 
        kwargs = self.get_form_kwargs(step)
        data = data or kwargs.get('data', None)
        files = files or kwargs.get('files', None)
        return super().get_form(step, data, files) 
