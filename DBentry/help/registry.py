
class HelpRegistry(object):
    
    def __init__(self):
        self._registry = {
            'models' : {}, 
            'forms' : {}, 
        }
        
    def register_model(self, model, help_object):
        if not self.is_registered(model):
            self._registry['models'][model] = help_object
        
    def register_form(self, url_name, help_object):
        if not self.is_registered(url_name):
            self._registry['forms'][url_name] = help_object
    
    def is_registered(self, obj):
        if isinstance(obj, str):
            return obj in self.get_registered_forms()
        from django.db.models import Model
        if issubclass(obj, Model):
            return obj in self.get_registered_models()
        
    def get_registered_models(self):
        return self._registry.get('models', {})
        
    def get_registered_forms(self):
        return self._registry.get('forms', {})
    
    def help_for_model(self, model):
        if self.is_registered(model):
            return self._registry['models'][model]

halp = HelpRegistry()    

def register(url_name = None):
    from DBentry.help.helptext import FormHelpText
    def helptext_wrapper(help_object):
        if url_name and issubclass(help_object, FormHelpText):
            halp.register_form(url_name, help_object)
        else:
            halp.register_model(help_object.model, help_object)
        return help_object
    return helptext_wrapper
