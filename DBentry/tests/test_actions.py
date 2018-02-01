"""
This is meant to test an action at its 'backend'. 
Probably not going to stay.
"""
# TODO: Since merging is now an action in actions.views these tests need to be reworked
#
#from .base import *
#
#from DBentry.admin import *
#
#class TestAdminActionsArtikel(ActionTestCase):
#    
#    model_admin_class = ArtikelAdmin
#    model = artikel
#    test_data_count = 3
#    
#    action = 'merge_records'
#        
#    def test_merge_records_low_count(self):
#        # qs.count() == 1
#        qs = self.model.objects.filter(pk=self.obj1.pk)
#        request = self.get_request()
#        merge_records = self.action_func
#        merge_records(self.model_admin, request, qs)
#        expected_message = 'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen'
#        messages = [str(msg) for msg in get_messages(request)]
#        self.assertTrue(expected_message in messages)
#        
#    def test_merge_records_not_allowed(self):
#        # qs.count() > 1 with different ausgaben => merge not allowed
#        the_new_guy = DataFactory().create_obj(artikel, create_new = True)
#        qs = self.model.objects.all()
#        request = self.get_request()
#        merge_records = self.action_func
#        response = merge_records(self.model_admin, request, qs)
#        self.assertEqual(response, None)
#    
#    def test_merge_records_success(self):
#        # qs.count() >1 with same ausgabe
#        qs = self.model.objects.all()
#        request = self.get_request()
#        merge_records = self.action_func
#        response = merge_records(self.model_admin, request, qs)
#        self.assertIsNotNone(response)
#        self.assertTrue('merge' in request.session)
#        self.assertEqual(response.status_code, 302) # 302 for redirect       
