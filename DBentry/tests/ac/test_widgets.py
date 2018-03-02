
from dal import autocomplete

from .base import *

from DBentry.forms import ArtikelForm
from DBentry.ac.widgets import *

class TestWrapping(TestCase):
    
    def test_wrap_success(self):
        widget = autocomplete.ModelSelect2(url='acaudio')
        self.assertIsInstance(wrap_dal_widget(widget), EasyWidgetWrapper)
        
    def test_wrap_no_reverse_match(self):
        # Try to wrap a widget with an explicit _nocreate option:
        # the wrapper should return the unchanged widget
        widget = autocomplete.ModelSelect2(url='acaudio__nocreate')
        self.assertNotIsInstance(wrap_dal_widget(widget), EasyWidgetWrapper)
        
    @skip("Test might require changing url conf during runtime.")
    def test_wrap_no_resolver_match(self):
        # This is a bit awkward. In order to reach that condition the widget's url
        # must be reverseable but must not be resolveable. 
        widget = autocomplete.ModelSelect2(url='acaudio__nocreate')
        self.assertNotIsInstance(wrap_dal_widget(widget), EasyWidgetWrapper)
        
    def test_wrap_with_no_dal_widget(self):
        # Do not wrap widgets that are not from dal
        from django import forms
        widget = forms.Textarea()
        self.assertNotIsInstance(wrap_dal_widget(widget), EasyWidgetWrapper)
        
class TestEasyWidgetWrapper(TestCase):
    
    def setUp(self):
        super().setUp()
        form = ArtikelForm()
        self.widget = wrap_dal_widget(form.fields['ausgabe'].widget)
        rel_opts = self.widget.related_model._meta 
        self.info = (rel_opts.app_label, rel_opts.model_name) 
    
    def test_get_related_url(self):
        #TODO: - /admin/DBentry/spielort/__fk__/change/
        #?                 ^^ ----
        #+ /admin/DBentry/ausgabe/__fk__/change/
        # WTF?

        form = ArtikelForm()
        self.widget = wrap_dal_widget(form.fields['ausgabe'].widget)
        rel_opts = self.widget.related_model._meta 
        self.info = (rel_opts.app_label, rel_opts.model_name) 
        url = self.widget.get_related_url(self.info, 'change', '__fk__')
        print("\n form fields", form.fields)
        print("form widget related_model", form.fields['ausgabe'].widget.choices.queryset.model._meta)
        print("self.info", self.info)
        print("self.widget", self.widget)
        print("rel_opts", self.widget.related_model._meta)
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
