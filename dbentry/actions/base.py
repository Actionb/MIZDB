from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple, Type, Union

from django import views
from django.contrib.admin import ModelAdmin, helpers
from django.contrib.admin.utils import display_for_field, get_fields_from_path
from django.db.models import Model, QuerySet
from django.db.models.options import Options
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.safestring import SafeText
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy

from dbentry.base.views import FixedSessionWizardView, MIZAdminMixin
from dbentry.utils import get_obj_link

SafeTextOrStr = Union[str, SafeText]

# TODO: remove MIZAdminMixin inheritance? If MIZAdminMixin is not required by
#  ConfirmationViewMixin methods or processes, it should be removed.


class ConfirmationViewMixin(MIZAdminMixin):
    """
    A mixin that controls the confirmation stage of an admin action.

    Attributes:
        - ``title`` (str): the title that is shown both in the template and
          in the browser title
        - ``action_reversible`` (bool): if False (which is the default), it is
          implied that this action will make a change that is not easily
          reversed. If False, a warning text is added to the template context.
        - ``non_reversible_warning`` (str): a text that warns the user that
          the action they are about to confirm is not reversible.
        - ``short_description`` (str): label for the action in the changelist
          dropdown menu.
        - ``action_name`` (str): name of the action as registered with the
          ModelAdmin. This is the value for the hidden input named "action"
          with which the ModelAdmin.response_action resolves the action to use.
        - ``view_helptext`` (str): a help text for this view
        - ``action_allowed_checks`` (list or tuple): list of callables or names
          of view methods that assess if the action is allowed. These checks
          must return a true boolean or None.
    """

    title: str = ''
    breadcrumbs_title: str = ''
    non_reversible_warning: str = gettext_lazy("Warning: This action is NOT reversible!")
    action_reversible: bool = False
    short_description: str = ''
    action_name: Optional[str] = None
    # TODO: remove view_helptext - add help texts to context data directly where
    #  needed/declared
    view_helptext: str = ''
    action_allowed_checks: Sequence = ()

    # Must declare these class attributes so as_view() accepts
    # 'model_admin' and 'queryset' as arguments.
    model_admin: ModelAdmin = None
    queryset: QuerySet = None

    def __init__(
            self, model_admin: ModelAdmin, queryset: QuerySet, *args: Any, **kwargs: Any
    ) -> None:
        # queryset and model_admin are passed in from initkwargs in
        # as_view(cls,**initkwargs).view(request)-> cls(**initkwargs)
        self.model_admin = model_admin
        self.queryset = queryset
        self.opts: Options = self.model_admin.opts
        self.model: Type[Model] = self.opts.model
        # Allow setting of custom action_names, otherwise use the class's name
        if not getattr(self, 'action_name', False):
            self.action_name = self.__class__.__name__
        super().__init__(*args, **kwargs)  # type: ignore[call-arg]

    def get_action_allowed_checks(self) -> Iterable[Callable]:
        """Resolve the checks to callables and yield them."""
        for check in self.action_allowed_checks:
            if isinstance(check, str) and hasattr(self, check):
                check = getattr(self.__class__, check)
            if not callable(check):
                continue
            yield check

    @property
    def action_allowed(self) -> bool:
        """
        Check if the action is allowed.

        Checks are called with keyword argument 'view' which is this instance.
        Assessment stops if a check returns False.
        """
        if not hasattr(self, '_action_allowed'):
            self._action_allowed = True
            for check in self.get_action_allowed_checks():
                # TODO: do not use is False:
                #  https://peps.python.org/pep-0008/#programming-recommendations
                #  at "Don’t compare boolean values to True or False using =="
                if check(view=self) is False:  # TODO: just use self as first arg, not a kwarg
                    self._action_allowed = False
                    break
        return self._action_allowed

    def perform_action(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError('Subclasses must implement this method.')  # pragma: no cover

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Optional[HttpResponse]:
        if not self.action_allowed:
            # The action is not allowed, redirect back to the changelist
            # TODO: shouldn't the user at least get a message that the action is not allowed?
            return None
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        defaults = {
            'queryset': self.queryset,
            'opts': self.opts,
            'action_name': self.action_name,
            'view_helptext': self.view_helptext,
            # action_checkbox_name is used for marking the (hidden) inputs
            # that hold the primary keys of the objects.
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        }

        # template variable to accurately address the objects of the queryset
        if self.queryset.count() == 1:
            defaults['objects_name'] = force_str(self.opts.verbose_name)
        else:
            defaults['objects_name'] = force_str(self.opts.verbose_name_plural)

        # Add model_admin and form media.
        if 'media' in context:
            media = context['media'] + self.model_admin.media
        else:
            media = self.model_admin.media
        if hasattr(self, 'get_form') and self.get_form():  # type: ignore[attr-defined]
            media += self.get_form().media  # type: ignore[attr-defined]
        # FIXME: need to remove 'media' from kwargs or the new default will be
        #  overridden!
        defaults['media'] = media

        # Add view specific variables.
        title = self.title or getattr(self, 'short_description', '')
        title = title % {'verbose_name_plural': self.opts.verbose_name_plural}
        breadcrumbs_title = self.breadcrumbs_title or title
        breadcrumbs_title = breadcrumbs_title % {
            'verbose_name_plural': self.opts.verbose_name_plural
        }

        defaults['title'] = title
        defaults['breadcrumbs_title'] = breadcrumbs_title
        if not self.action_reversible:
            defaults['non_reversible_warning'] = self.non_reversible_warning
        else:
            # TODO: remove else - the template won't complain if this item was
            #  missing
            defaults['non_reversible_warning'] = ''

        context.update({**defaults, **kwargs})
        return context


class ActionConfirmationView(ConfirmationViewMixin, views.generic.FormView):
    """
    Base view for all action views.

    It provides the template with a list of changeform-links to objects that
    are going to be changed by this action. This list is created by the
    ``compile_affected_objects`` method.

    Attributes:
        - ``affected_fields`` (list): the model fields whose values should be
          displayed in the summary of objects affected by this action
    """
    # TODO: mention that the template expects a MIZAdminForm (a form with fieldsets)!
    template_name: str = 'admin/action_confirmation.html'

    affected_fields: list

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # TODO: just make affected_fields a tuple - then this check won't be necessary:
        if not hasattr(self, 'affected_fields') or self.affected_fields is None:
            self.affected_fields = []

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        # TODO: wouldn't it be smarter to just check what kind of request it is
        #  and act accordingly (GET: no data form, POST: data form)?
        #  It makes no sense to validate the form on a GET request?
        # Note that actions are initiated by POSTing the action select form!
        if 'action_confirmed' not in self.request.POST:
            # Only pass in 'data' if the user tries to confirm an action.
            # Do not try to validate the form if it is the first time the
            # user sees the form.
            if 'data' in kwargs:
                del kwargs['data']
            if 'files' in kwargs:
                del kwargs['files']
        return kwargs

    def form_valid(self, form: Form) -> None:
        self.perform_action(form.cleaned_data)
        # We always want to be redirected back to the changelist the action
        # originated from (request.get_full_path()).
        # If we return None, options.ModelAdmin.response_action will do
        # the redirect for us.
        return None

    def compile_affected_objects(self) -> List[Tuple[SafeTextOrStr, List[SafeTextOrStr]]]:
        """
        Compile a list of the objects that are affected by this action.

        Display them as a link to that object's respective change page,
        if possible. If the action is aimed at the values of particular fields
        of the objects, present those values as a nested list.
        """
        # TODO: this is only used by the edit jahrgang action
        def linkify(model_instance):
            object_link = get_obj_link(
                model_instance, self.request.user,
                self.model_admin.admin_site.name, blank=True
            )
            if "</a>" in object_link:
                # get_obj_link returned a full link;
                # add the model's verbose_name.
                return format_html(
                    '{model_name}: {object_link}',
                    model_name=capfirst(model_instance._meta.verbose_name),
                    object_link=object_link
                )
            else:
                # get_obj_link couldn't create a link and has simply returned
                # {model_name}: force_str(obj)
                return object_link

        objects = []
        for obj in self.queryset:
            # Investigate the field paths in affected_fields:
            # - if the path follows a relation, add a link to each related
            #   object that is going to be impacted by the action's changes
            # - if it's a field of the object, get that field's value
            sub_list = []
            for field_path in self.affected_fields:
                field = get_fields_from_path(self.opts.model, field_path)[0]
                if field.is_relation:
                    related_pks = self.queryset.filter(pk=obj.pk).values_list(
                        field.name, flat=True
                    ).order_by(field.name)
                    for pk in related_pks:
                        if not pk:
                            # values_list() will also gather None values
                            continue  # pragma: no cover
                        related_obj = field.related_model.objects.get(pk=pk)
                        sub_list.append(linkify(related_obj))
                else:
                    value = display_for_field(getattr(obj, field.name), field, '---')
                    verbose_name = field.verbose_name
                    if verbose_name == field.name.replace('_', ' '):
                        # The field has the default django verbose_name
                        verbose_name = verbose_name.title()
                    sub_list.append("{}: {}".format(verbose_name, str(value)))
            if self.affected_fields:
                links = (linkify(obj), sub_list)
            else:
                links = (linkify(obj),)  # type: ignore[assignment]
            objects.append(links)
        return objects

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                'affected_objects': self.compile_affected_objects(),
            }
        )
        context.update(**kwargs)
        return context


class WizardConfirmationView(ConfirmationViewMixin, FixedSessionWizardView):
    """Base view for action views that require a SessionWizardView."""

    template_name: str = 'admin/action_confirmation_wizard.html'

    # A dictionary of helptexts for every step: {step:helptext}
    # TODO: remove view_helptext - add helptexts to context data directly where
    #  needed/declared
    view_helptext: dict  # type: ignore[assignment]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(WizardConfirmationView, self).__init__(*args, **kwargs)
        if not hasattr(self, 'view_helptext') or self.view_helptext is None:
            self.view_helptext = {}
        self.qs = self.queryset  # WizardView wants it so

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        if self.steps.current in self.view_helptext:
            context['view_helptext'] = self.view_helptext.get(self.steps.current)
        return context

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpRequest:
        # Actions are always POSTED, but to initialize the SessionWizardView
        # a GET request is expected.
        # We work around this by checking if there's a 'current_step'
        # in the request.
        if request.POST.get(self.get_prefix(request) + '-current_step') is not None:
            # the 'previous' form was a wizard form, call WizardView.post()
            return super().post(request, *args, **kwargs)
        else:
            # we just got here from the changelist -- prepare the storage engine
            self.storage.reset()

            # reset the current step to the first step.
            self.storage.current_step = self.steps.first
            return self.render(self.get_form())

    def done(self, *args: Any, **kwargs: Any) -> None:
        # The 'final' method of a WizardView. It is called from render_done
        # with some args and kwargs we do not care about.
        # By default, force a redirect back to the changelist by returning None
        try:
            self.perform_action()
        finally:
            return None
