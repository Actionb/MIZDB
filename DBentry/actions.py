
from django.utils.translation import ugettext as _, ugettext_lazy
from django.shortcuts import redirect  
from django.urls import reverse

from .views import MIZAdminMixin, OptionalFormView

def merge_records(model_admin, request, queryset):
    if queryset.count()==1:
        model_admin.message_user(request,'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen', 'warning')
        return
    if not model_admin.merge_allowed(request, queryset):
        return
    request.session['merge'] = {'qs_ids': list(queryset.values_list('pk', flat=True)), 'success_url' : request.get_full_path()}
    return redirect(reverse('merge', kwargs=dict(model_name=model_admin.opts.model_name)))
merge_records.short_description = ugettext_lazy("Merge selected %(verbose_name_plural)s")#'Datensätze zusammenfügen'
merge_records.perm_required = ['merge']

class ActionConfirmationView(MIZAdminMixin, OptionalFormView):
    #TODO: text stuff
    #TODO: put in an actual form for user input
    
    template_name = 'admin/action_confirmation.html'
    queryset = None
    model_admin = None
    opts = None
    action_name = None
    
    def __init__(self, *args, **kwargs):
        # queryset and model_admin are passed in from initkwargs in as_view(cls,**initkwargs).view(request)-> cls(**initkwargs)
        self.queryset = kwargs.pop('queryset')
        self.model_admin = kwargs.pop('model_admin')
        if not getattr(self, 'action_name', False): # Allow setting of custom action_names, otherwise use the class's name
            self.action_name = self.__class__.__name__
        self.opts = self.model_admin.opts
        super(ActionConfirmationView, self).__init__(*args, **kwargs)
        
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
            objs.append([str(obj)])
        return objs
    
    def post(self, request, *args, **kwargs):
        if request.POST.get('action_confirmed', False):
            # User has confirmed the action  --- OptionalFormView will figure out the correct response to give.
            return super(ActionConfirmationView, self).post(request, *args, **kwargs)
        elif request.POST.get('action_aborted', False):
            # User aborted the action, redirect back to the changelist
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
        
        from django.contrib.admin import helpers
        context.update(
            dict(
                title                   =   _("Are you sure?"),
                objects_name            =   objects_name,
                queryset                =   self.queryset,
                affected_objects        =   self.compile_affected_objects(), 
                opts                    =   self.opts,
                action_checkbox_name    =   helpers.ACTION_CHECKBOX_NAME,
                media                   =   self.model_admin.media, #TODO: form.media?
                action_name             =   self.action_name, # see below (line contrib.admin.options:1255)
            )
        )
        #NOTE: having to specify action_name so the view does not magically (looking at you javascript) redirect to 
        # the deletion_confirmation template/view... 
        # if the action_name is the reason the view finds its way back into the 'right' post method (i.e. here NOT in deletion_confirmation)
        # does that mean I need a view per action anyway - making CBVs useless for this?
        return context
        
class BulkJahrgang(ActionConfirmationView):
    
    short_description = 'Jahrgang hinzufügen'
    perm_required = ['change']
    
    def action_allowed(self):
        if self.queryset.values('magazin_id').distinct().count() != 1:
            msg_text = "Aktion abgebrochen: ausgewählte Ausgaben stammen von mehr als einem Magazin."
            self.model_admin.message_user(self.request, msg_text, 'error')
            return False
        return True
    
    def perform_action(self, form_cleaned_data):
        self.queryset.order_by().update(jahrgang=form_cleaned_data['jahrgang'])

