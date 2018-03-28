
from dal import autocomplete

from .base import *

from DBentry.forms import ArtikelForm
from DBentry.ac.widgets import *
        
class TestEasyWidgetWrapper(TestCase):
    
    def setUp(self):
        super().setUp()
        form = ArtikelForm()
        self.widget = EasyWidgetWrapper(form.fields['ausgabe'].widget, ausgabe, 'id')
        rel_opts = self.widget.related_model._meta 
        self.info = (rel_opts.app_label, rel_opts.model_name) 
    
    def test_get_related_url(self):
        url = self.widget.get_related_url(self.info, 'change', '__fk__')
        self.assertEqual(url, "/admin/DBentry/ausgabe/__fk__/change/", msg='info: {}'.format(self.info))
        
        url = self.widget.get_related_url(self.info, 'add')
        self.assertEqual(url, "/admin/DBentry/ausgabe/add/")
        
        url = self.widget.get_related_url(self.info, 'delete', '__fk__')
        self.assertEqual(url, "/admin/DBentry/ausgabe/__fk__/delete/")
        
    def test_get_context_can_change(self):
        context = self.widget.get_context('Beep', ['1'], {'id':1})
        self.assertTrue(context.get('can_change_related', False))
        self.assertEqual(context.get('change_related_template_url'), "/admin/DBentry/ausgabe/__fk__/change/")
        
    def test_get_context_can_add(self):
        context = self.widget.get_context('Beep', ['1'], {'id':1})
        self.assertTrue(context.get('can_add_related', False))
        self.assertEqual(context.get('add_related_url'), "/admin/DBentry/ausgabe/add/")
        
    def test_get_context_can_delete(self):
        self.widget.can_delete_related = True
        context = self.widget.get_context('Beep', ['1'], {'id':1})
        self.assertTrue(context.get('can_delete_related', False))
        self.assertEqual(context.get('delete_related_template_url'), "/admin/DBentry/ausgabe/__fk__/delete/")
