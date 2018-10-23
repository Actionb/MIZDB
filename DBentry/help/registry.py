
from DBentry.utils import get_model_admin_for_model
from django.urls import reverse, exceptions


class HelpRegistry(object):
    
    def __init__(self, *admin_sites):
        self.admin_sites = admin_sites
        self._registry = {}
        self._modeladmins, self._formviews = set(), set()
        
    def is_registered(self, view_class):
        return view_class in self._registry
        
    def get_registered_modeladmins(self):
        return self._modeladmins
        
    def get_registered_forms(self):
        return self._formviews
        
    def helptext_for_view(self, view_class):
        """
        Returns the helptext class registered with that view_class.
        """
        if self.is_registered(view_class):
            helptext, url_name = self._registry[view_class]
            return helptext
        
    def helptext_for_model(self, model):
        """
        Returns the ModelAdminHelpText class that is registered to that model.
        Since we store the ModelAdmin instance associated with that model instead of the model itself, the ModelAdmin must be looked up first. 
        """
        # Used by ModelAdminHelpText.inline_helptexts
        model_admin = get_model_admin_for_model(model)
        if not model_admin:
            return
        return self.helptext_for_view(model_admin)
            
    def help_url_for_view(self, view_class):
        """
        Returns the full path to the help page for this view_class (view_class is either a ModelAdmin or a FormView).
        """
        # Used by templatetags.object_tools
        if self.is_registered(view_class):
            helptext, url_name = self._registry[view_class]
            try:
                return reverse(url_name)
            except exceptions.NoReverseMatch:
                pass
        return ''
    
    def get_urls(self):
        #TODO: iterate over _modeladmins and _formviews to keep an order
        from django.conf.urls import url
        from DBentry.help.views import ModelAdminHelpView, FormHelpView, HelpIndexView
        
        urlpatterns = []
        for view_class, (helptext, url_name) in self._registry.items():
            init_kwargs = {'registry':self}
            if view_class in self._modeladmins:
                # This is a help page for a ModelAdmin
                model_name = view_class.model._meta.model_name
                regex = r'^{}/'.format(model_name)
                init_kwargs.update(model_admin = view_class, helptext_class = helptext)
                view_func = ModelAdminHelpView.as_view(**init_kwargs)
            elif view_class in self._formviews:
                # A help page for a custom FormView
                regex = '^{}/'.format(url_name.replace('help_', ''))
                init_kwargs.update(target_view_class = view_class, helptext_class = helptext)
                view_func = FormHelpView.as_view(**init_kwargs)
            else:
                # TODO: raise exception
                raise
            urlpatterns.append(url(regex, view_func, name = url_name))
            
        # Don't forget the index page
        urlpatterns.append(
            url(r'', HelpIndexView.as_view(registry = self), name = 'help_index')
        )
        return urlpatterns
        
    @property
    def urls(self):
        return self.get_urls(), None, None
    
    def register(self, helptext, url_name):
        """
        - helptext + (optional) url_name passed in
        - if ModelAdminHelpText: associate with the *ModelAdmin* instance registered to that model class
        - if FormViewHelpText: associate with the helptext's target_view_class
        """
        from DBentry.help.helptext import ModelAdminHelpText, FormViewHelpText
        
        if issubclass(helptext, ModelAdminHelpText):
            # This is a helptext for a ModelAdmin instance
            # Look up the ModelAdmin instance belonging to that model and use that in the registry
            view_class = get_model_admin_for_model(helptext.model, *self.admin_sites)
            if view_class is None:
                raise AttributeError("No ModelAdmin for model found.", helptext.model)
            if url_name is None:
                url_name = 'help_' + helptext.model._meta.model_name
            self._modeladmins.add(view_class)
        elif issubclass(helptext, FormViewHelpText):
            # A helptext for a FormView
            view_class = helptext.target_view_class
            if view_class is None:
                raise AttributeError("Helptext class has no target_view_class set.", helptext)
            if url_name is None:
                url_name = 'help_' + str(view_class)
            self._formviews.add(view_class)
        else:
            raise TypeError("Unknown helptext class:", helptext)
        self._registry[view_class] = (helptext, url_name)
        
halp = HelpRegistry()

def register(url_name = None, registry = None):
    
    from DBentry.help.helptext import BaseHelpText
    
    def helptext_wrapper(helptext):
        if not issubclass(helptext, BaseHelpText):
            raise ValueError('Wrapped helptext class must subclass BaseHelpText.')
        
        _registry = registry or halp
        if not isinstance(_registry, HelpRegistry):
            raise ValueError('registry must subclass HelpRegistry')
            
        _registry.register(helptext, url_name)
        
        return helptext
    return helptext_wrapper

