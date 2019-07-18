from django.utils.translation import gettext_lazy
from django.utils.encoding import force_text
from django.contrib.admin.utils import get_fields_from_path
from django import views

from DBentry.utils import get_obj_link
from DBentry.views import MIZAdminMixin, FixedSessionWizardView

class ConfirmationViewMixin(MIZAdminMixin):
    """A mixin that controls the confirmation stage of an admin action.

    Attributes:
        title (str): the title that is shown both in the template and
            in the browser title
        non_reversible_warning (str): a text that warns the user that
            the action they are about to confirm is not reversible.
        action_reversible (bool): set to True, if this action performs
            an operation that is not easily reversed.
        short_description (str): label for the action in the changelist
            dropdown menu.
        perm_required (list or tuple): list of permission codewords required to
            access the action.
            See DBentry.admin.base.MIZModelAdmin.get_actions().
        action_name (str): context variable that will be used on the template
            so django redirects back here through response_action
            (line contrib.admin.options:1255)
        view_helptext (str): a help text for this view
    """

    title = ''
    breadcrumbs_title = ''
    non_reversible_warning = gettext_lazy("Warning: This action is NOT reversible!")
    action_reversible = False
    short_description = ''
    perm_required = ()
    action_name = None
    view_helptext = ''

    # Must declare these class attributes so as_view() accepts
    # 'model_admin' and 'queryset' as arguments.
    model_admin = None
    queryset = None

    def __init__(self, model_admin, queryset, *args, **kwargs):
        # queryset and model_admin are passed in from initkwargs in
        # as_view(cls,**initkwargs).view(request)-> cls(**initkwargs)
        self.model_admin = model_admin
        self.queryset = queryset
        self.opts = self.model_admin.opts
        self.model = self.opts.model
        # Allow setting of custom action_names, otherwise use the class's name
        if not getattr(self, 'action_name', False):
            self.action_name = self.__class__.__name__
        super().__init__(*args, **kwargs)

    def action_allowed(self):
        return True

    def perform_action(self, form_cleaned_data = None):
        raise NotImplementedError('Subclasses must implement this method.')

    def dispatch(self, request, *args, **kwargs):
        if not self.action_allowed():
            # The action is not allowed, redirect back to the changelist
            return None
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

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
            defaults['objects_name'] = force_text(self.opts.verbose_name)
        else:
            defaults['objects_name'] = force_text(self.opts.verbose_name_plural)

        # Add model_admin and form media.
        if 'media' in context:
            media = context['media'] + self.model_admin.media
        else:
            media = self.model_admin.media
        if hasattr(self, 'get_form') and self.get_form():
            media += self.get_form().media
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
            defaults['non_reversible_warning'] = ''

        context.update({**defaults, **kwargs})
        return context

class ActionConfirmationView(ConfirmationViewMixin, views.generic.FormView):

    template_name = 'admin/action_confirmation.html'

    affected_fields = [] # these are the model fields that should be displayed in the summary of objects affected by this action

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'action_confirmed' not in self.request.POST:
            # Only pass in 'data' if the user tries to confirm an action. 
            # Do not try to validate the form if it is the first time the user sees the form. 
            if 'data' in kwargs: del kwargs['data']
            if 'files' in kwargs: del kwargs['files']
        return kwargs

    def form_valid(self, form):
        self.perform_action(form.cleaned_data)
        # We always want to be redirected back to the changelist the action originated from (request.get_full_path()).
        # If we return None, options.ModelAdmin.response_action will do the redirect for us.
        return None

    def compile_affected_objects(self):
        """
        Compile a list of the objects that are affected by this action.
        Display them as a link to that object's respective change page, if possible.
        If the action is aimed at the values of particular fields of the objects, present those values as a nested list.
        """        
        def linkify(obj):
            return get_obj_link(obj, self.request.user, self.model_admin.admin_site.name)

        objs = []
        for obj in self.queryset:
            sub_list = [linkify(obj)]
            affected_fields = self.affected_fields
            if affected_fields:
                flds = []
                for field_path in affected_fields:
                    field = get_fields_from_path(self.opts.model, field_path)[0]
                    if field.is_relation:
                        related_pks = self.queryset.filter(pk=obj.pk).values_list(field.name, flat=True)
                        for pk in related_pks:
                            if pk: # values() will also gather None values
                                related_obj = field.related_model.objects.get(pk=pk)
                                flds.append(linkify(related_obj))
                    else:
                        value = getattr(obj, field.name)
                        if value is None:
                            value = '---'
                        verbose_name = field.verbose_name
                        if verbose_name == field.name.replace('_', ' '):
                            # The field has the default django verbose_name
                            verbose_name = verbose_name.title()
                        flds.append("{}: {}".format(verbose_name, str(value)))
                sub_list.append(flds)
            objs.append(sub_list)
        return objs

    def get_context_data(self, *args, **kwargs):
        context = super(ActionConfirmationView, self).get_context_data(*args, **kwargs)

        context.update({
            'affected_objects': self.compile_affected_objects(), 
        })
        context.update(**kwargs)
        return context


class WizardConfirmationView(ConfirmationViewMixin, FixedSessionWizardView):

    template_name = 'admin/action_confirmation_wizard.html' 

    # A dictionary of helptexts for every step: {step:helptext}
    view_helptext = {}

    def __init__(self, *args, **kwargs):
        super(WizardConfirmationView, self).__init__(*args, **kwargs)
        self.qs = self.queryset # WizardView wants it so

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.steps.current in self.view_helptext:
            context['view_helptext'] = self.view_helptext.get(self.steps.current)
        return context

    def post(self, request, *args, **kwargs):
        # Actions are always POSTED, but to initialize the SessionWizardView a GET request is expected.
        # We work around this by checking if there's a 'current_step' in the request.
        if request.POST.get(self.get_prefix(request)+'-current_step') is not None:
            # the 'previous' form was a wizard form, call WizardView.post()
            return super(WizardConfirmationView, self).post(request, *args, **kwargs)
        else:
            # we just got here from the changelist -- prepare the storage engine
            self.storage.reset()

            # reset the current step to the first step.
            self.storage.current_step = self.steps.first
            return self.render(self.get_form())  

    def done(self, *args, **kwargs): 
        # The 'final' method of a WizardView. It is called from render_done with some args and kwargs we do not care about.
        # By default, force a redirect back to the changelist by returning None
        try:
            self.perform_action() 
        finally:
            return None
