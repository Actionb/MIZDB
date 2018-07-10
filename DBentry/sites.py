
from collections import OrderedDict

from django.contrib import admin  
from django.apps import apps 
from django.views.decorators.cache import never_cache

class MIZAdminSite(admin.AdminSite):
    site_header = 'MIZDB'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = []
    
    def register_tool(self, view):
        self.tools.append(view)
        
    def app_index(self, request, app_label, extra_context=None):
        if app_label == 'DBentry':
            # Redirect to the 'tidied' up index page of the main page
            return self.index(request, extra_context)
        return super(MIZAdminSite, self).app_index(request, app_label, extra_context)
    
    @never_cache
    def index(self, request, extra_context=None): 
        extra_context = extra_context or {}
        extra_context['admintools'] = {}
        for tool in self.tools:
            if tool.show_on_index_page(request) and tool.permission_test(request):
                extra_context['admintools'][tool.url_name] = tool.index_label
        # Sort by index_label, not by url_name
        extra_context['admintools'] = OrderedDict(sorted(extra_context['admintools'].items(), key=lambda x: x[1]))
        response = super(MIZAdminSite, self).index(request, extra_context)
        app_list = response.context_data['app_list']
        
        index = None
        try:
            index = next(i for i, d in enumerate(app_list) if d['app_label'] == 'DBentry')
        except StopIteration:
            # No app with label 'DBentry' found
            return response
            
        if index is not None:
            DBentry_dict = app_list.pop(index) # the dict containing data for the DBentry app with keys: {app_url,name,has_module_perms,models,app_label}
            model_list = DBentry_dict.pop('models')
            categories = OrderedDict()
            #TODO: translation
            categories['Archivgut'] = []
            categories['Stammdaten'] = []
            categories['Sonstige'] = []
            
            for m in model_list:
                # m is a dict with keys {admin_url, name (i.e. the label), perms, object_name (i.e. the model name), add_url}
                model_admin = self.get_admin_model(m.get('object_name'))
                model_category = model_admin.get_index_category()
                if model_category not in categories:
                    categories['Sonstige'] = [m]
                else:
                    categories[model_category].append(m)
                    
            for category, models in categories.items():
                new_fake_app = DBentry_dict.copy()
                new_fake_app['name'] = category
                new_fake_app['models'] = models
                app_list.append(new_fake_app)
            response.context_data['app_list'] = app_list
        return response

    def get_admin_model(self, model):
        if isinstance(model, str):
            model_name = model.split('.')[-1]
            try:
                model = apps.get_model('DBentry', model_name)
            except LookupError:
                return None
        return self._registry.get(model, None)
        
miz_site = MIZAdminSite()

def register_tool(tool_view):
    from DBentry.views import MIZAdminToolViewMixin
    
    if not issubclass(tool_view, MIZAdminToolViewMixin):
        raise ValueError('Wrapped class must subclass MIZAdminToolView.')

    miz_site.register_tool(tool_view)
    
    return tool_view
    
