from unittest.mock import patch

from .base import AdminTestCase, mockv

from django.contrib.admin.views.main import ChangeList, DisallowedModelAdminLookup

from DBentry.models import artikel, magazin
from DBentry.admin import ArtikelAdmin, MagazinAdmin
from DBentry.changelist import MIZChangeList, IncorrectLookupParameters

#TODO: review after having moved the ordering of ausgabe querysets from changelist to querysets
        
class TestChangeList(AdminTestCase):
    
    model_admin_class = ArtikelAdmin
    model = artikel
    test_data_count = 3
        
    def test_init(self):
        cl = self.get_changelist(self.get_request())
        self.assertTrue(hasattr(cl, 'request'))
        self.assertTrue(hasattr(cl, '_annotations'))
    
    def test_init_pagevar(self):
        # Assert that MIZChangeList can handle the PAGE_VAR
        with self.assertNotRaises(IncorrectLookupParameters):
            self.get_changelist(self.get_request(data = {'p':['1']}))
    
    def test_init_errorvar(self):
        # Assert that MIZChangeList can handle the ERROR_FLAG
        with self.assertNotRaises(IncorrectLookupParameters):
            self.get_changelist(self.get_request(data = {'e':['1']}))

    @patch.object(ChangeList, 'get_filters_params')
    def test_get_filters_params_handles_QueryDict(self, super_get_filters_params):
        # Assert that get_filters_params does not throw an AttributeError due to trying to delete a key
        # from an immutable QueryDict
        cl = self.get_changelist(self.get_request())
        request = self.get_request(data={'p':['1'], 'e':['1']})
        super_get_filters_params.return_value = request.GET
        with self.assertNotRaises(Exception):
            cl.get_filters_params(request.GET)
        
    def test_get_filters_empty_params(self):
        # get_filters returns filter_specs, bool(filter_specs), lookup_params, use_distinct
        cl = self.get_changelist(self.get_request())
        expected = ( [], False, {}, False )
        self.assertEqual(cl.get_filters(cl.request), expected)
    
    def test_get_filters_DisallowedModelAdminLookup(self):
        cl = self.get_changelist(self.get_request())
        cl.model_admin.lookup_allowed = mockv(False)
        with self.assertRaises(DisallowedModelAdminLookup):
            cl.get_filters(self.get_request(data = {'ausgabe':'1'}))
            
    def test_get_filters_build_remaining_lookup_params(self):
        cl = self.get_changelist(self.get_request())
        remaining_lookup_params = cl.get_filters(self.get_request(data= {'ausgabe':'1'}))[2]
        self.assertIn('ausgabe', remaining_lookup_params)
        self.assertEqual(remaining_lookup_params['ausgabe'], '1')
        
    def test_get_filters_FieldDoesNotExist(self):
        cl = self.get_changelist(self.get_request())
        with self.assertRaises(IncorrectLookupParameters):
            cl.get_filters(self.get_request(data = {'beep': 'boop'}))

    def test_get_queryset_qs_redirect(self):
        session = self.client.session
        ids = [i.pk for i in self.test_data]
        session['qs'] = dict(id__in=ids)
        session.save()
        
        cl = self.get_changelist(self.get_request())
        cl_qs = cl.get_queryset(cl.request).order_by('pk')
        expected_qs =  self.model.objects.filter(pk__in=ids).order_by('pk')
        self.assertListEqual(list(cl_qs), list(expected_qs))
        
    def test_get_queryset_IncorrectLookupParameters(self):
        cl = self.get_changelist(self.get_request())
        with self.assertRaises(IncorrectLookupParameters):
            cl.get_queryset(self.get_request(data = {'genre': ['a', 'b']})) 
            
class TestChangeListAnnotations(AdminTestCase):
    
    model = magazin
    model_admin_class = MagazinAdmin
    test_data_count = 0
            
    def test_annotations(self):
        # Assert that dictionary admin_order_fields are interpreted to be annotations and that those annotations are 
        # added correclty to the final queryset.
        # MagazinAdmin should have a callable list_display item that would require annotation: anz_ausgaben
        try:
            # syntax magic *snort*: dict items unpacking directly into variables: 
            # ((key_a, value_a), (key_b, value_b), ...) == dict_items([('a', 1), ('b', 2), ...])
            (order_field, annotation), = self.model_admin.anz_ausgaben.admin_order_field.items()
        except ValueError:
            raise ValueError("admin_order_field for annotations should be a single item dictionary. Is: %s" % self.model_admin.anz_ausgaben.admin_order_field)
        
        # Get the index of 'anz_ausgaben' and send a request with the ORDER_VAR 'o' set to that index to get the ChangeList to evaluate 
        # its list_display items.
        list_display = self.model_admin.get_list_display(self.get_request())
        idx = list_display.index('anz_ausgaben')
        cl = self.get_changelist(self.get_request(data = {'o': str(idx)}))
        self.assertIsInstance(cl, MIZChangeList, msg = '%s must be a subclass of MIZChangeList' % cl.__class__.__name__)
        self.assertIn(self.model_admin.anz_ausgaben.admin_order_field, cl._annotations)
        self.assertIn(order_field, cl.queryset.query.order_by)
        self.assertIn(order_field, cl.queryset.query.annotations)
        
        
