from .base import AdminTestCase

from django.contrib.admin.views.main import ORDER_VAR

from DBentry.models import ausgabe
from DBentry.admin import AusgabenAdmin
from DBentry.changelist import MIZChangeList

class TestChangeListAnnotations(AdminTestCase):
    
    model = ausgabe
    model_admin_class = AusgabenAdmin
    test_data_count = 0
    
    def test_get_ordering_field(self):
        list_display = self.model_admin.get_list_display(self.get_request())
        idx = list_display.index('anz_artikel') # + 1 as 'action_checkbox' is now the first part in list_display
        cl = self.get_changelist(self.get_request(data = {ORDER_VAR: str(idx)}))
        self.assertEqual(cl.get_ordering_field('anz_artikel'), 'anz')
            
    def test_annotations(self):
        # Assert that dictionary admin_order_fields are interpreted to be annotations and that those annotations are 
        # added correclty to the final queryset.
        # AusgabenAdmin should have a callable list_display item that would require annotation: anz_artikel
        order_field, func, expression, extra = self.model_admin.anz_artikel.admin_order_field
        
        # Get the index of 'anz_artikel' and send a request with the ORDER_VAR 'o' set to that index to get the ChangeList to evaluate 
        # its list_display items.
        list_display = self.model_admin.get_list_display(self.get_request())
        idx = list_display.index('anz_artikel') + 1  # + 1 as 'action_checkbox' is now the first part in list_display
        cl = self.get_changelist(self.get_request(data = {ORDER_VAR: str(idx)}))
        self.assertIsInstance(cl, MIZChangeList, msg = '%s must be a subclass of MIZChangeList' % cl.__class__.__name__)
        self.assertIn(self.model_admin.anz_artikel.admin_order_field, cl._annotations)
        self.assertIn(order_field, cl.queryset.query.order_by)
        self.assertIn(order_field, cl.queryset.query.annotations)
        annotation = cl.queryset.query.annotations['anz']
        self.assertIsInstance(annotation, func)
        self.assertTrue(annotation.distinct)
        
