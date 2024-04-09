from typing import Any, Callable, Iterable, Optional, Sequence, Type, Union, TYPE_CHECKING

from django import views
from django.contrib import messages
from django.contrib.admin import ModelAdmin, helpers
from django.contrib.admin.utils import display_for_field, get_fields_from_path, model_format_dict
from django.db.models import Model, QuerySet
from django.db.models.options import Options
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.urls import NoReverseMatch
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.safestring import SafeText
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy
from formtools.wizard.views import SessionWizardView

from dbentry.utils.html import create_hyperlink
from dbentry.utils.url import get_change_url

if TYPE_CHECKING:
    from dbentry.site.views.base import BaseListView  # noqa

SafeTextOrStr = Union[str, SafeText]
ViewOrModelAdmin = Union["BaseListView", ModelAdmin]


def get_object_link(request: HttpRequest, obj: Model, namespace: str) -> SafeText:
    """
    Return a safe string containing the model name and a link to the change
    page of ``obj``.
    """
    model_name = capfirst(obj._meta.verbose_name)
    try:
        url = get_change_url(request, obj, namespace)
    except NoReverseMatch:
        url = ""
    if url:
        link = create_hyperlink(url, str(obj), target="_blank")
    else:
        link = force_str(obj)
    return format_html("{model_name}: {object_link}", model_name=model_name, object_link=link)


class ActionMixin(object):
    """
    A view mixin for action views.

    It adds attributes shared by action views. It also adds a system that checks
    whether the action is allowed.

    Attributes:
        - ``title`` (str): the title that is shown both in the template and
          in the browser title
        - ``action_reversible`` (bool): if False (which is the default), it is
          implied that this action will make a change that is not easily
          reversed. If False, a warning text is added to the template context.
        - ``non_reversible_warning`` (str): a text that warns the user that
          the action they are about to confirm is not reversible.
        - ``action_name`` (str): name of the action as registered with the
          changelist view or the ModelAdmin. This is the value for the hidden
          input named "action" with which the changelist view resolves the
          action to use.
        - ``view_helptext`` (str): a help text for this view
        - ``action_allowed_checks`` (list or tuple): list of callables or names
          of view methods that assess whether the action is allowed. The checks
          are called with the view instance as the only argument.
        - ``url_namespace`` (str): the namespace for reversing view names
        - ``view`` (ListView or ModelAdmin): the changelist or model admin that
          called this action.
    """

    title: str = ""
    action_reversible: bool = False
    non_reversible_warning: str = gettext_lazy("Warning: This action is NOT reversible!")
    action_name: str = ""
    view_helptext: str = ""
    action_allowed_checks: Sequence = ()
    url_namespace: str = ""

    # These will be passed in as initkwargs, sp they must be declared as class
    # attributes or as_view will reject them:
    queryset: QuerySet = None
    view: ViewOrModelAdmin = None

    def __init__(self, *, queryset: QuerySet, view: ViewOrModelAdmin = None, **kwargs: Any) -> None:
        self.view = view
        self.queryset = queryset
        self.opts: Options = self.queryset.query.get_meta()
        self.model: Type[Model] = self.opts.model
        # Allow setting of custom action_names, otherwise use the class's name
        if not self.action_name:
            self.action_name = self.__class__.__name__
        super().__init__(**kwargs)

    def get_action_allowed_checks(self) -> Iterable[Callable]:
        """Resolve the checks to callables and yield them."""
        for check in self.action_allowed_checks:
            if isinstance(check, str) and hasattr(self, check):
                # Return the unbound function instead of the instance method:
                check = getattr(self.__class__, check)
            if not callable(check):
                continue
            yield check

    def action_allowed(self) -> bool:
        """Check if the action is allowed."""
        for check in self.get_action_allowed_checks():
            if not check(self):
                return False
        return True

    def perform_action(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement this method.")  # pragma: no cover

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Optional[HttpResponse]:
        if not self.action_allowed():
            # The action is not allowed, redirect back to the changelist.
            return None
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]

    def get_context_data(self, **kwargs: Any) -> dict:
        from dbentry.site.views.base import ACTION_SELECTED_ITEM

        defaults = {
            "queryset": self.queryset,
            "opts": self.opts,
            "action_name": self.action_name,
            "view_helptext": self.view_helptext,
            # action_checkbox_name is used for marking the (hidden) inputs
            # that hold the primary keys of the objects.
            "action_checkbox_name": ACTION_SELECTED_ITEM,
        }

        # template variable to accurately address the objects of the queryset
        if self.queryset.count() == 1:
            defaults["objects_name"] = force_str(self.opts.verbose_name)
        else:
            defaults["objects_name"] = force_str(self.opts.verbose_name_plural)

        defaults["title"] = self.title % model_format_dict(self.model)

        if not self.action_reversible:
            defaults["non_reversible_warning"] = self.non_reversible_warning

        kwargs = {**defaults, **kwargs}
        return super().get_context_data(**kwargs)  # type: ignore[misc]

    def message_user(
        self, request: HttpRequest, level: int, message: str, extra_tags: str = "", fail_silently: bool = False
    ) -> None:
        """Send a user message using Django messages."""
        messages.add_message(request, level, message, extra_tags, fail_silently)


class AdminActionMixin(ActionMixin):
    """A mixin for actions that are to be used on the admin site."""

    model_admin: ModelAdmin = None
    breadcrumbs_title: str = ""

    def __init__(self, *, model_admin: ModelAdmin, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.model_admin = model_admin
        self.admin_site = self.model_admin.admin_site
        self.url_namespace = self.admin_site.name

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)  # type: ignore[misc]

        breadcrumbs_title = self.breadcrumbs_title or context["title"]
        context["breadcrumbs_title"] = breadcrumbs_title % model_format_dict(self.model)

        # Add model admin and form media.
        if "media" in context:
            media = context["media"] + self.model_admin.media
        else:
            media = self.model_admin.media
        if hasattr(self, "get_form") and self.get_form():  # type: ignore[attr-defined]
            media += self.get_form().media  # type: ignore[attr-defined]
        context["media"] = media
        # ModelAdmin uses a different name for the selection checkboxes:
        context["action_checkbox_name"] = helpers.ACTION_CHECKBOX_NAME
        return context

    def message_user(
        self, request: HttpRequest, level: int, message: str, extra_tags: str = "", fail_silently: bool = False
    ) -> None:
        """Send a user message using admin messages."""
        # model_admin.message_user accepts the args in different order to
        # maintain backwards compatibility.
        self.model_admin.message_user(request, message, level, extra_tags, fail_silently)


class ActionConfirmationView(ActionMixin, views.generic.FormView):
    """
    A view that requires the user to confirm the action.

    The view presents the user with a confirmation form (via the template) and
    an overview of the objects affected by the action.

    Attributes:
        - ``display_fields`` (tuple): the model fields whose values should be
          displayed in the summary of objects affected by this action
    """

    template_name: str = "mizdb/action_confirmation.html"

    display_fields: tuple = ()

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        if "action_confirmed" not in self.request.POST:
            # Only pass in 'data' if the user tries to confirm an action.
            # Do not try to validate the form if it is the first time the
            # user sees the form.
            # Note that action requests are always POST requests.
            if "data" in kwargs:
                del kwargs["data"]
            if "files" in kwargs:
                del kwargs["files"]
        return kwargs

    def form_valid(self, form: Form) -> None:
        self.perform_action(form.cleaned_data)
        # We always want to be redirected back to the changelist the action
        # originated from (request.get_full_path()).
        # If we return None, options.ModelAdmin.response_action will do
        # the redirect for us.
        return None

    def get_objects_list(self) -> list:
        """
        Compile a list of the objects that would be changed by this action.

        Returns a list of 2-tuples, where the first item is a link to the
        change page of an object, and the second may be a nested list of the
        values (which may include yet more links) of fields declared in
        self.display_fields.
        """
        objects = []
        for obj in self.queryset:
            # Investigate the field paths in display_fields:
            # - if the path follows a relation, add a link to each related
            #   object that is going to be impacted by the action's changes
            # - if it's a field of the object, get that field's value
            sub_list = []
            for field_path in self.display_fields:
                field = get_fields_from_path(self.opts.model, field_path)[0]
                if field.is_relation:
                    related_pks = (
                        self.queryset.filter(pk=obj.pk).values_list(field.name, flat=True).order_by(field.name)
                    )
                    for pk in related_pks:
                        if not pk:
                            # values_list() will also gather None values
                            continue  # pragma: no cover
                        related_obj = field.related_model.objects.get(pk=pk)
                        sub_list.append(get_object_link(self.request, related_obj, self.url_namespace))
                else:
                    value = display_for_field(getattr(obj, field.name), field, "---")
                    verbose_name = field.verbose_name
                    if verbose_name == field.name.replace("_", " "):
                        # The field has the default django verbose_name
                        verbose_name = verbose_name.title()
                    sub_list.append("{}: {}".format(verbose_name, str(value)))
            if self.display_fields:
                links = (get_object_link(self.request, obj, self.url_namespace), sub_list)
            else:
                links = (get_object_link(self.request, obj, self.url_namespace),)  # type: ignore[assignment]
            objects.append(links)
        return objects

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["object_list"] = self.get_objects_list()
        return context


class AdminActionConfirmationView(AdminActionMixin, ActionConfirmationView):
    """
    An ActionConfirmationView that uses a template adjusted for the admin site.

    Note that the template expects an MIZAdminForm with fieldsets.
    """

    template_name: str = "admin/action_confirmation.html"


class WizardConfirmationView(ActionMixin, SessionWizardView):
    """Base view for action views that use the formtools SessionWizardView."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpRequest:
        # Note that action requests are always POST requests.
        if request.POST.get(self.get_prefix(request) + "-current_step") is None:
            # The previous form was not a wizard form, or it didn't have a step
            # set. Assume that the user just got here from the changelist, and
            # treat this as an initial get request for the WizardView.
            return self.get(request)
        else:
            # The previous form was most likely a wizard form.
            return super().post(request, *args, **kwargs)

    def done(self, *args: Any, **kwargs: Any) -> None:
        # The 'final' method of a WizardView.
        # By default, redirect back to the changelist by returning None.
        try:
            self.perform_action()
        finally:
            return None
