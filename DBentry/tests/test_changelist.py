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
    
    def setUp(self):
        super(TestChangeList, self).setUp()
        self.init_data = dict(
            model = self.model, 
            list_display = self.model_admin.list_display, 
            list_display_links = self.model_admin.list_display_links, 
            list_filter = self.model_admin.list_filter, 
            date_hierarchy = self.model_admin.date_hierarchy, 
            search_fields = self.model_admin.search_fields, 
            list_select_related = self.model_admin.list_select_related,
            list_per_page = self.model_admin.list_per_page, 
            list_max_show_all = self.model_admin.list_max_show_all, 
            list_editable = self.model_admin.list_editable, 
            model_admin = self.model_admin
        )
    
    def get_cl(self, data={}):
        request = self.get_request(path=self.changelist_path, data=data)
        return MIZChangeList(request, **self.init_data.copy())
        
    def test_init(self):
        cl = self.get_cl()
        self.assertTrue(hasattr(cl, 'request'))
    
    def test_init_pagevar(self):
        # Assert that MIZChangeList can handle the PAGE_VAR
        request = self.get_request(path=self.changelist_path, data={'p':['1']})
        with self.assertNotRaises(IncorrectLookupParameters):
            MIZChangeList(request, **self.init_data.copy())
    
    def test_init_errorvar(self):
        # Assert that MIZChangeList can handle the ERROR_FLAG
        request = self.get_request(path=self.changelist_path, data={'e':['1']})
        with self.assertNotRaises(IncorrectLookupParameters):
            MIZChangeList(request, **self.init_data.copy())
    
    def test_get_filters(self):
        request_data = dict(genre = [1, 2])
        cl = self.get_cl(request_data)
        (filter_specs, has_filters, remaining_lookup_params, use_distinct) = cl.get_filters(cl.request)

    @patch.object(ChangeList, 'get_filters_params')
    def test_get_filters_params_handles_QueryDict(self, super_get_filters_params):
        # Assert that get_filters_params does not throw an AttributeError due to trying to delete a key
        # from an immutable QueryDict
        cl = self.get_cl()
        request = self.get_request(data={'p':['1'], 'e':['1']})
        super_get_filters_params.return_value = request.GET
        with self.assertNotRaises(Exception):
            cl.get_filters_params(request.GET)
        
    def test_get_filters_empty_params(self):
        cl = self.get_cl()
        expected = ( [], False, {}, False )
        self.assertEqual(cl.get_filters(cl.request), expected)
    
    def test_get_filters_DisallowedModelAdminLookup(self):
        cl = self.get_cl()
        cl.model_admin.lookup_allowed = mockv(False)
        with self.assertRaises(DisallowedModelAdminLookup):
            cl.get_filters(self.get_request(data = {'ausgabe':'1'}))
            
    def test_get_filters_build_remaining_lookup_params(self):
        request = self.get_request(path=self.changelist_path, data={'ausgabe':'1'})
        cl = self.get_cl()
        remaining_lookup_params = cl.get_filters(request)[2]
        self.assertIn('ausgabe', remaining_lookup_params)
        self.assertEqual(remaining_lookup_params['ausgabe'], '1')
        
    def test_get_filters_FieldDoesNotExist(self):
        cl = self.get_cl()
        request_data = dict(beep = 'boop')
        request = self.get_request(path=self.changelist_path, data=request_data)
        
        with self.assertRaises(IncorrectLookupParameters):
            cl.get_filters(request)
            
    def test_get_queryset(self):
        pass

    def test_get_queryset_qs_redirect(self):
        session = self.client.session
        ids = [i.pk for i in self.test_data]
        session['qs'] = dict(id__in=ids)
        session.save()
        
        cl = self.get_cl()
        cl_qs = cl.get_queryset(cl.request).order_by('pk')
        expected_qs =  self.model.objects.filter(**dict(id__in=ids)).order_by('pk')
        self.assertListEqual(list(cl_qs), list(expected_qs))
        
    def test_get_queryset_IncorrectLookupParameters(self):
        cl = self.get_cl()
        request_data = dict(
            genre = ['a', 'b'] # should be int
        )
        request = self.get_request(path=self.changelist_path, data=request_data)
        
        with self.assertRaises(IncorrectLookupParameters):
            cl.get_queryset(request)
            
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
        
        
