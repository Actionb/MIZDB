from typing import Any, Optional, Type

from django import views
from django.contrib.admin import AdminSite
from django.contrib.auth.mixins import UserPassesTestMixin
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from formtools.wizard.views import SessionWizardView

from dbentry.sites import miz_site


class MIZAdminMixin(object):
    """A mixin that adds admin_site specific context (each_context) to the view."""

    title: str = ''
    site_title: str = 'MIZDB'
    breadcrumbs_title: str = ''
    admin_site: AdminSite = miz_site

    def __init__(self, *args: Any, admin_site: Optional[AdminSite] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if admin_site:
            self.admin_site = admin_site

    def get_context_data(self, **kwargs: Any) -> dict:
        context: dict = super().get_context_data(**kwargs)  # type: ignore[misc]

        # Context variables title & site_title for the html document's title.
        # (used by admin/base_site.html)
        if self.title:
            context.setdefault('title', self.title)
        if self.site_title:
            context.setdefault('site_title', self.site_title)
        if self.breadcrumbs_title:
            context.setdefault('breadcrumbs_title', self.breadcrumbs_title)
        # Enable popups behaviour for custom views.
        context['is_popup'] = '_popup' in self.request.GET  # type: ignore[attr-defined]
        # Add the admin site context.
        site_context = self.admin_site.each_context(self.request)  # type: ignore[attr-defined]
        return {**site_context, **context}


class OptionalFormView(views.generic.FormView):
    """A FormView that does not require form_class to be set."""

    def get_form(self, form_class: Optional[Type[Form]] = None) -> Optional[Form]:
        """
        Return an instance of the form to be used in this view, or None if no
        form class given.
        """
        if self.get_form_class() is None:
            # The form is optional.
            return None
        return super().get_form(form_class)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        form = self.get_form()
        if form is None or form.is_valid():
            # Treat an optional form like a valid form.
            return self.form_valid(form)
        else:
            # This view has a form_class set, but the form is invalid.
            return self.form_invalid(form)


class FixedSessionWizardView(SessionWizardView):
    """Subclass of SessionWizardView that fixes some quirks."""

    def get_context_data(self, **kwargs: Any) -> dict:
        # SessionWizardView expects 'form' as required positional argument.
        # TODO: this isn't the case anymore, SessionWizardView plays nice with
        #  form as a kwarg.
        return super().get_context_data(kwargs.pop('form', None), **kwargs)

    def get_form(
            self,
            step: Optional[int] = None,
            data: Optional[dict] = None,
            files: Optional[dict] = None
    ) -> Form:
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

        If we wanted to keep changes to the request payload made in
        get_form_kwargs, we need to call super with explicit data (and files)
        kwargs derived from get_form_kwargs.
        """
        # TODO: it doesn't look like any views using this view class use
        #  get_form_kwargs to override data/files - so this 'fix' here might
        #  not be needed.
        if step is None:
            step = self.steps.current
        kwargs = self.get_form_kwargs(step)
        data = data or kwargs.get('data', None)
        files = files or kwargs.get('files', None)
        return super().get_form(step, data, files)


class SuperUserOnlyMixin(UserPassesTestMixin):
    """Only allow superusers to access the view."""

    def test_func(self) -> bool:
        """test_func for UserPassesTestMixin."""
        # noinspection PyUnresolvedReferences
        return self.request.user.is_superuser
