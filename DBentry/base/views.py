from django import views

from formtools.wizard.views import SessionWizardView

from DBentry.sites import miz_site


class MIZAdminMixin(object):
    """Add admin_site specific context (each_context) to the view."""

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
    """Subclass of SessionWizardView that fixes some quirks."""

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
