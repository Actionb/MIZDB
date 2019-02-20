import contextlib

from ..base import AdminTestCase, RequestTestCase, add_urls
from ..mixins import CreateFormMixin, CreateViewMixin

from DBentry.help.registry import HelpRegistry


class HelpRegistryMixin(object):
    """
    A mixin to include a HelpRegistry instance in the test cases.
    Included is the 'add_urls' contextmanager to override the ROOT_URLCONF with the registry's urls.
    """

    def setUp(self):
        super().setUp()
        self.registry = HelpRegistry()
    
    @contextlib.contextmanager
    def add_urls(self, path_prefix = '^admin/help/'):
        """
        By default, urls created by a HelpRegistry are resolved using the settings.ROOT_URLCONF.
        tests.base.add_urls is another contextmanager that overrides the setting for that to inject another set of urls.
        In this case, that would be the urls of this instance's registry.
        """
        with add_urls(self.registry.get_urls(), path_prefix):
            yield
        
class HelpTextMixin(object):
    """
    A mixin that provides easy access to instances of a declared helptext_class.
    """
    
    helptext_class = None
    
    def get_helptext_initkwargs(self):
        return {}
        
    def get_helptext_instance(self, **kwargs):
        helptext_initkwargs = self.get_helptext_initkwargs()
        helptext_initkwargs.update(kwargs)
        return self.helptext_class(**helptext_initkwargs)
        
class FormViewHelpTextMixin(HelpTextMixin, CreateFormMixin):
    """
    An extension of CreateFormMixin to allow creation of FormHelpTexts.
    """
    
    def get_helptext_instance(self, **kwargs):
        self.helptext_class.form_class = self.get_dummy_form_class()
        return super().get_helptext_instance(**kwargs)
        
class RegisteredHelpTextMixin(HelpRegistryMixin, HelpTextMixin):
    """
    Auto-registers a single HelpText object.
    """
    
    url_name = None
    
    def setUp(self):
        super().setUp()
        self.registry.register(helptext = self.helptext_class, url_name = self.url_name)
        
class ModelAdminHelpTextTestCase(RegisteredHelpTextMixin, RequestTestCase):
    
    def get_helptext_initkwargs(self):
        # ModelAdminHelpTexts require a registry argument 
        helptext_initkwargs = super().get_helptext_initkwargs()
        helptext_initkwargs['registry'] = self.registry
        return helptext_initkwargs
        
    def get_helptext_instance(self, request = None, **kwargs):
        # request is a required argument for ModelAdminHelpText objects
        request = request or self.get_request()
        return super().get_helptext_instance(request=request, **kwargs)
        
class HelpViewMixin(HelpRegistryMixin, CreateViewMixin):
    """
    An extension of CreateViewMixin to provide necessary initkwargs for HelpViews.
    """
    
    def get_view_initkwargs(self):
        return {}
        
    def get_view(self, **kwargs):
        view_initkwargs = self.get_view_initkwargs()
        view_initkwargs.update(kwargs)
        return super().get_view(**view_initkwargs)

class RegisteredHelpViewMixin(RegisteredHelpTextMixin, HelpViewMixin):
    
    def get_view_initkwargs(self):
        view_initkwargs = super().get_view_initkwargs()
        view_initkwargs['helptext_class'] = self.helptext_class
        return view_initkwargs
        
class ModelHelpViewTestCase(RegisteredHelpViewMixin, AdminTestCase):
    
    def get_view_initkwargs(self):
        view_initkwargs = super().get_view_initkwargs()
        view_initkwargs['model_admin'] = self.model_admin
        view_initkwargs['registry'] = self.registry
        return view_initkwargs
