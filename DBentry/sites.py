
from collections import OrderedDict

from django.contrib import admin  
from django.apps import apps 
from django.views.decorators.cache import never_cache

from .models import wip_models, main_models

class MIZAdminSite(admin.AdminSite):
    site_header = 'MIZDB'
    
    tools = []
    
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
            index = next(i for (i, d) in enumerate(app_list) if d['app_label'] == 'DBentry')
        except:
            return response
            
        if index is not None:
            DBentry_dict = app_list.pop(index)
            model_list = DBentry_dict.pop('models')
        
            DBentry_main = DBentry_dict.copy()
            DBentry_main['name'] = 'Hauptkategorien'
            DBentry_main['models'] = [] # or deepcopy DBentry_dict
            DBentry_side = DBentry_dict.copy()
            DBentry_side['name'] = 'Nebenkategorien'
            DBentry_side['models'] = []
            
            for m in model_list:
                if m.get('object_name', '') in main_models:
                    DBentry_main['models'].append(m)
                else:
                    DBentry_side['models'].append(m)
                    
            if DBentry_main['models']:
                app_list.extend([DBentry_main])
            if DBentry_side['models']:
                app_list.extend([DBentry_side])
                
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
    
