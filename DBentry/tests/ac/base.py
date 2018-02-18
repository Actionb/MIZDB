from ..base import *

from DBentry.ac.views import *

@tag("dal")
class ACViewTestCase(TestDataMixin, ViewTestCase, LoggingTestMixin):
    
    model = None
    create_field = None
    
    def view(self, request=None, args=None, kwargs=None, model = None, create_field = None, forwarded = None, q = None):
        #DBentry.ac.views behave slightly different in their as_view() method
        self.view_class.model = model or self.model
        self.view_class.create_field = create_field or self.create_field
        self.view_class.forwarded = forwarded or {}
        self.view_class.q = q or ''
        return super(ACViewTestCase, self).view(request, args, kwargs)
        

@tag("dal")
class ACViewTestMethodMixin(object):
    
    view_class = ACBase
    test_data_count = 3
    add_relations = True
    _alias_accessor_name = ''
    
    @property
    def alias(self):
        if not self._alias_accessor_name:
            if hasattr(self, 'model'):
                alias_accessor_name = self.model._meta.model_name + '_alias_set'
                if alias_accessor_name in self.model.get_search_fields():
                    self._alias_accessor_name = alias_accessor_name
        return self._alias_accessor_name
    
    def test_do_ordering(self):
        # Test covered by test_get_queryset
        view = self.view()
        expected = self.model._meta.ordering
        qs_order = view.do_ordering(self.queryset).query.order_by
        self.assertListEqualSorted(qs_order, expected)
        
    def test_apply_q(self):
        # Test that an object can be found through any of its search_fields
        view = self.view()
        search_fields = view.flds
        for search_field in search_fields:
            q = self.qs_obj1.values_list(search_field, flat=True).first()
            if q:
                view.q = str(q)
                self.assertIn(self.obj1, view.apply_q(self.queryset), msg="search_field: {}, q: {}".format(search_field, str(q)))
        if self.alias:
            # Find an object through its alias
            alias = getattr(self.obj1, self.alias).first()
            view.q = str(alias)
            self.assertIn(self.obj1, view.apply_q(self.queryset))
        
    def test_get_queryset(self):
        # Note that ordering does not matter here, testing for the correct order is the job of `test_do_ordering` and apply_q would mess it up anyhow
        request = self.get_request()
        view = self.view(request)
        qs = view.get_queryset().values_list('pk', flat=True)
        expected = self.queryset.values_list('pk', flat=True)
        self.assertListEqualSorted(qs, expected)
    
    def test_flds_prop(self):
        self.assertListEqualSorted(self.view().flds, self.model.get_search_fields())
        
    def test_get_create_option(self):
        request = self.get_request()
        view = self.view(request)
        create_option = view.get_create_option(context={}, q='Beep')
        if view.has_create_field():
            self.assertEqual(len(create_option), 1)
            self.assertEqual(create_option[0].get('id'), 'Beep')
            self.assertEqual(create_option[0].get('text'), 'Erstelle "Beep"') #TODO: translation
            self.assertTrue(create_option[0].get('create_id'))
        else:
            self.assertEqual(len(create_option), 0)
        
    @tag('logging')
    def test_create_object_no_log_entry(self):
        # no request set on view, no log entry should be created
        view = self.view()
        if view.has_create_field():
            obj = view.create_object('Beep')
            with self.assertRaises(AssertionError):
                self.assertLoggedAddition(obj)    
        
    @tag('logging')
    def test_create_object_with_log_entry(self):
        # request set on view, log entry should be created
        request = self.get_request()
        view = self.view(request)
        if view.has_create_field():
            obj = view.create_object('Boop')
            self.assertLoggedAddition(obj)   
