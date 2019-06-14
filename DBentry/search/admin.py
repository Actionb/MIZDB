from DBentry.search.forms import searchform_factory
            
class AdminSearchFormMixin(object):
    
    #TODO: change_list_template attribute
    #TODO: what if we dont want a search_form?
    
    search_form_kwargs = None
    search_form_class = None
    search_form_wrapper = None # Wrapper class such as django admin's AdminForm wrapper

    def get_search_form_class(self, **kwargs):
        if self.search_form_class is not None:
            return self.search_form_class
        factory_kwargs = self.search_form_kwargs or {}
        factory_kwargs.update(kwargs)
        return searchform_factory(model = self.model, **factory_kwargs)

    def get_search_form(self, **form_kwargs):
        form_class = self.get_search_form_class()
        form = form_class(**form_kwargs)
        if callable(self.search_form_wrapper):
            form = self.search_form_wrapper(form)
        self.search_form = form
        return form
        
class ChangelistSearchFormMixin(object):
    
    def get_filters_params(self, params=None):
        lookup_params = super().get_filters_params(params)
        try:
            form = self.model_admin.get_search_form(data = params)
        except AttributeError:
            # model_admin does not have the get_search_form method;
            # most likely, the ModelAdmin does not include the 
            # advanced_search_form mixin.
            return lookup_params
        # Preliminarily remove all params that belong to the search form
        # so that, if the form is invalid, the form's data is not 
        # going to be used to filter the changelist's queryset.
        #NOTE: should form.clean do this? 
        for field_name in form.fields:
            if field_name in lookup_params: 
                del lookup_params[field_name]
                
        lookup_params.update(form.get_filter_params())
        return lookup_params
        
    
