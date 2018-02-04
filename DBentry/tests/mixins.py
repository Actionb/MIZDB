from .data import DataFactory

class TestDataMixin(object):
    
    model = None
    queryset = None
    test_data = []
    test_data_count = 0
    add_relations = True
    
    @classmethod
    def setUpTestData(cls):
        super(TestDataMixin, cls).setUpTestData()
        if cls.test_data_count:
            cls.test_data = DataFactory().create_data(cls.model, count=cls.test_data_count, add_relations = cls.add_relations)
        for c, obj in enumerate(cls.test_data, 1):
            setattr(cls, 'obj' + str(c), obj)
        
    def setUp(self):
        super(TestDataMixin, self).setUp()
        for c, obj in enumerate(self.test_data, 1):
            obj.refresh_from_db()
            setattr(self, 'qs_obj' + str(c), self.model.objects.filter(pk=obj.pk)) #NOTE: or in setUpTestData?
        self.queryset = self.model.objects.all()
        
class CreateViewMixin(object):
    """
    Simulate the view being instantiated through as_view()().
    """
    
    view_class = None
    
    def view(self, request=None, args=None, kwargs=None, **initkwargs):
        self.view_class.request = request
        self.view_class.args = args
        self.view_class.kwargs = kwargs
        return self.view_class(**initkwargs)

class CreateFormMixin(object):
    """
    Quickly create forms.
    """
    
    form_class = None
    valid_data = {}
    
    def get_form_class(self):
        return self.form_class
    
    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        return form_class(**kwargs)
        
    def get_valid_form(self):
        form = self.get_form(data=self.valid_data.copy())
        if self.valid_data and not form.is_valid():
            raise Exception('self.valid_data did not contain valid data!')
        return form
        
class CreateFormViewMixin(CreateFormMixin, CreateViewMixin):
    """
    Attempts to use the form_class given in view_class as the form's class.
    """   
        
    def get_form_class(self):
        if getattr(self.view_class, 'form_class', None) is not None:
            return self.view_class.form_class
        else:
            return super(CreateFormViewMixin, self).get_form_class()
