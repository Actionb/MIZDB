
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text

from DBentry.views import MIZAdminMixin, OptionalFormView
from .forms import makeSelectionForm

class ActionConfirmationView(MIZAdminMixin, OptionalFormView):
    #TODO: text stuff
    
    template_name = 'admin/action_confirmation.html'
    queryset = None
    model_admin = None
    opts = None
    action_name = None
    
    fields = None # these are the model fields that should be displayed in the 'selection form'
    
    def __init__(self, *args, **kwargs):
        # queryset and model_admin are passed in from initkwargs in as_view(cls,**initkwargs).view(request)-> cls(**initkwargs)
        self.queryset = kwargs.pop('queryset')
        self.model_admin = kwargs.pop('model_admin')
        if not getattr(self, 'action_name', False): # Allow setting of custom action_names, otherwise use the class's name
            self.action_name = self.__class__.__name__
        self.opts = self.model_admin.opts
        super(ActionConfirmationView, self).__init__(*args, **kwargs)
        
    def get_form_class(self):
        if self.fields and not self.form_class: 
            # default to the makeForm factory function if there is no form_class given
            return makeSelectionForm(self.model_admin.model, fields=self.fields)
        return super(ActionConfirmationView, self).get_form_class()
        
    def form_valid(self, form):
        # OptionalFormView returns this when either the (optional) form is not given or the form is valid.
        self.perform_action(None if form is None else form.cleaned_data)
        
        # We always want to be redirected back to the changelist the action originated from (request.get_full_path()).
        # If we return None, options.ModelAdmin.response_action will do the redirect for us.
        return None
        
    def action_allowed(self):
        return True
        
    def perform_action(self, form_cleaned_data = None):
        raise NotImplementedError('Subclasses must implement this method.')
        
    def compile_affected_objects(self):
        #TODO: link_list this // NestedObjects stuff -> needs to show relevant data (jg,bestand,etc.)
        objs = []
        for obj in self.queryset:
            objs.append(str(obj))
        return objs
    
    def post(self, request, *args, **kwargs):
        if request.POST.get('action_confirmed', False):
            # User has confirmed the action  --- OptionalFormView will figure out the correct response to give:
            # if a form is not present: perform the action without additional (form) data
            # if a form is present and valid: perform the action with form data
            # if a form is present and invalid: show the confirmation page again
            return super(ActionConfirmationView, self).post(request, *args, **kwargs)
        elif request.POST.get('action_aborted', False):
            # User aborted the action, redirect back to the changelist
            # In the django builtin delete_selected_confirmation this was handled via javascript -> window.history.back()
            # Which would not work if back() took you back to an earlier 'instance' of this view, 
            # as we're using POST exclusively and you cannot back into a POSTED page.
            return None
        else:
            if self.action_allowed():
                # Display the confirmation page
                return self.render_to_response(self.get_context_data(*args, **kwargs))    
            else:
                # The action was not allowed
                return None
    
    def get_context_data(self, *args, **kwargs):
        context = super(ActionConfirmationView, self).get_context_data(*args, **kwargs)
        
        if len(self.queryset) == 1:
            objects_name = force_text(self.opts.verbose_name)
        else:
            objects_name = force_text(self.opts.verbose_name_plural)
        
        media = self.model_admin.media
        if self.get_form():
            media += self.get_form().media
        
        from django.contrib.admin import helpers
        context.update(
            dict(
                title                   =   _("Are you sure?"),
                objects_name            =   objects_name,
                queryset                =   self.queryset,
                affected_objects        =   self.compile_affected_objects(), 
                opts                    =   self.opts,
                action_checkbox_name    =   helpers.ACTION_CHECKBOX_NAME,
                media                   =   media,
                action_name             =   self.action_name, # see below
            )
        )
        context.update(**kwargs)
        # action_name is a context variable that will be used on the template to tell django to direct back here
        # (through response_action (line contrib.admin.options:1255))
        return context
