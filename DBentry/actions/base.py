
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text
from django.contrib.admin.utils import get_fields_from_path

from DBentry.utils import get_obj_link
from DBentry.views import MIZAdminMixin, OptionalFormView, FixedSessionWizardView
from .forms import makeSelectionForm

class ConfirmationViewMixin(MIZAdminMixin):
    
    title = '' # the title that is shown both in the template and in the browser
    breadcrumbs_title = ''
    non_reversible_warning = _("Warning: This action is NOT reversible!")
    action_reversible = False # if this action performs an operation that is not easily reversed, be as annoying as possible to wake the user up
    
    queryset = None
    model_admin = None
    opts = None
    action_name = None
    model = None
    
    view_helptext = ''
    
    def __init__(self, *args, **kwargs):
        # queryset and model_admin are passed in from initkwargs in as_view(cls,**initkwargs).view(request)-> cls(**initkwargs)
        self.queryset = kwargs.pop('queryset')
        self.model_admin = kwargs.pop('model_admin')
        if not getattr(self, 'action_name', False): # Allow setting of custom action_names, otherwise use the class's name
            self.action_name = self.__class__.__name__
        self.opts = self.model_admin.opts
        self.model = self.opts.model
        super(ConfirmationViewMixin, self).__init__(*args, **kwargs)
        
    def action_allowed(self):
        return True
        
    def perform_action(self, form_cleaned_data = None):
        raise NotImplementedError('Subclasses must implement this method.')
        
    def dispatch(self, request, *args, **kwargs):
        if not self.action_allowed():
            # The action is not allowed, redirect back to the changelist
            return None
        return super(ConfirmationViewMixin, self).dispatch(request, *args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        context = super(ConfirmationViewMixin, self).get_context_data(*args, **kwargs)
        
        if len(self.queryset) == 1:
            objects_name = force_text(self.opts.verbose_name)
        else:
            objects_name = force_text(self.opts.verbose_name_plural)
        
        media = self.model_admin.media
        if hasattr(self, 'get_form') and self.get_form():
            media += self.get_form().media
            
        from django.contrib.admin import helpers
        context.update(
            dict(
                title                   =   self.title or getattr(self, 'short_description', ''),
                objects_name            =   objects_name,
                queryset                =   self.queryset,
                opts                    =   self.opts,
                action_checkbox_name    =   helpers.ACTION_CHECKBOX_NAME, # this variable is used for marking the (hidden) inputs that hold the primary keys of the objects
                media                   =   media,
                action_name             =   self.action_name, # action_name is a context variable that will be used on the template to tell django to direct back here (through response_action (line contrib.admin.options:1255))
                view_helptext           =   self.view_helptext, 
                non_reversible_warning  =   self.non_reversible_warning if not self.action_reversible else '', 
                breadcrumbs_title       =   self.breadcrumbs_title or getattr(self, 'short_description', ''), 
            )
        )
        context.update(**kwargs)
        return context
    

class ActionConfirmationView(ConfirmationViewMixin, OptionalFormView):
    
    template_name = 'admin/action_confirmation.html'
    
    affected_fields = [] # these are the model fields that should be displayed in the summary of objects affected by this action
    
    # Related to the makeSelectionForm form factory. Can be omitted if form_class is given or no form needs to be displayed
    fields = [] # these are the model fields that should be displayed in the 'selection form'
    help_texts = {} # help_texts for the makeSelectionForm
    labels = {} # labels  for the makeSelectionForm
        
    def get_form_class(self):
        if self.fields and not self.form_class: 
            # default to the makeSelectionForm factory function if there is no form_class given
            return makeSelectionForm(self.model_admin.model, fields=self.fields, labels=self.labels, help_texts=self.help_texts)
        return super(ActionConfirmationView, self).get_form_class()

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }
        # Only pass in 'data' if the user tries to confirm an action. 
        # Do not try to validate the form if it is the first time the user sees the form. (avoids 'INVALID' field errors popping up, scaring the user)
        if self.request.method in ('POST', 'PUT') and 'action_confirmed' in self.request.POST:
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs
        
    def form_valid(self, form):
        # OptionalFormView returns this when either the (optional) form is not given or the form is valid.
        self.perform_action(None if form is None else form.cleaned_data)
        
        # We always want to be redirected back to the changelist the action originated from (request.get_full_path()).
        # If we return None, options.ModelAdmin.response_action will do the redirect for us.
        return None
        
    def compile_affected_objects(self):
        """
        Compile a list of the objects that are affected by this action.
        Display them as a link to that object's respective change page, if possible.
        If the action is aimed at the values of particular fields of the objects, present those values as a nested list.
        """
        
        def linkify(obj, opts):
            return get_obj_link(obj, opts, self.request.user, self.model_admin.admin_site)
        
        objs = []
        for obj in self.queryset:
            sub_list = [linkify(obj, self.opts)]
            affected_fields = self.affected_fields or self.fields
            if affected_fields:
                flds = []
                for field_path in affected_fields:
                    field = get_fields_from_path(self.opts.model, field_path)[0]
                    if field.is_relation:
                        related_pks = self.queryset.filter(pk=obj.pk).values_list(field.name, flat=True)
                        for pk in related_pks:
                            if pk: # values() will also gather None values
                                related_obj = field.related_model.objects.get(pk=pk)
                                flds.append(linkify(related_obj, field.related_model._meta))
                    else:
                        value = getattr(obj, field.name)
                        if value is None:
                            value = '---'
                        flds.append("{}: {}".format(field.verbose_name, str(value)))
                sub_list.append(flds)
            objs.append(sub_list)
        return objs
    
    def get_context_data(self, *args, **kwargs):
        context = super(ActionConfirmationView, self).get_context_data(*args, **kwargs)
            
        context.update(
            dict(
                affected_objects        =   self.compile_affected_objects(), 
            )
        )
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

    def done(self, form_list, **kwargs): 
        # The 'final' method of a WizardView.
        # By default, force a redirect back to the changelist by returning None
        self.perform_action() 
        return None