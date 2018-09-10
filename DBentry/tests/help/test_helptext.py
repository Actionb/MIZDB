from ..base import *

from django import forms as django_forms

from DBentry.help.helptext import *

class TestHTFunctions(TestCase):
    
    def test_formfield_to_modelfield(self):
        model_field = formfield_to_modelfield(artikel, 'schlagzeile', None)
        self.assertEqual(model_field, artikel._meta.get_field('schlagzeile'))
        
        formfield = django_forms.ModelChoiceField(queryset = magazin.objects.all())
        model_field = formfield_to_modelfield(artikel, 'ausgabe__magazin', formfield)
        self.assertEqual(model_field, ausgabe._meta.get_field('magazin'))
        
        self.assertIsNone(formfield_to_modelfield(artikel, 'doesnotexist', None))
        
class TestWrapper(TestCase):
    
    def test_sidenav(self):
        wrapped = Wrapper(id = 'test', val = 'beep boop')
        self.assertEqual(wrapped.sidenav(), '<a href="#test">Test</a>')
        
        wrapped.val = ['beep', 'boop']
        expected = "".join([
            '<a href="#test">Test</a>',
            '<ul>', 
            '<li><a href="#test-1">beep</a></li>',
            '<li><a href="#test-2">boop</a></li>',
            '</ul>', 
        ])
        self.assertEqual(wrapped.sidenav(), expected)
        
    def test_html(self):
        wrapped = Wrapper(id = 'test', val = 'beep boop')
        self.assertEqual(wrapped.html(), '<span id=test>beep boop</span>')
        
        wrapped.val = ['beep', 'boop']
        expected = "".join([
            '<ul>', 
            '<li id=test-1 class="">beep<br></li>', 
            '<li id=test-2 class="">boop<br></li>', 
            '</ul>', 
        ])
        self.assertEqual(wrapped.html(), expected)
        
        wrapped.val = [
            {'id':'coffee', 'label':'is good', 'text':'Alice and Bob enjoy a drink'}, 
            {'id':'tea', 'label':'not bad either', 'classes':'helpitem'}, 
        ]
        expected = "".join([
            '<ul>', 
            '<li id=coffee class="">is good<br>Alice and Bob enjoy a drink</li>', 
            '<li id=tea class="helpitem">not bad either<br></li>', 
            '</ul>', 
        ])
        self.assertEqual(wrapped.html(), expected)
        
class TestBaseHelpText(TestCase):
    
    def test_for_context(self):        
        # Assert that for_context skips help_items that refer to an attribute that was not declared
        instance = BaseHelpText()
        instance.Alice = None
        instance.help_items = ['Alice']
        instance.__init__()
        context = instance.for_context()
        self.assertIn('help_items', context)
        self.assertFalse(context['help_items'])
        
        # Assert that for_context accepts a 'help_item' of type str
        instance = BaseHelpText()
        instance.Alice = 'Beep'
        instance.help_items = ['Alice']
        instance.__init__()
        context = instance.for_context()
        self.assertIn('help_items', context)
        self.assertEqual(len(context['help_items']), 1)
        alice_help = context['help_items'][0]
        self.assertIsInstance(alice_help, Wrapper)
        self.assertEqual(alice_help.id, 'Alice')
        self.assertEqual(alice_help.label, 'Alice')
        self.assertEqual(alice_help.val, 'Beep')
        
        # Assert that for_context accepts a help_item of type list/tuple
        instance = BaseHelpText()
        instance.Alice = 'Beep'
        instance.Bob = 'Boop'
        instance.help_items = [('Alice', ), ['Bob', 'BobLabel']]
        instance.__init__()
        context = instance.for_context()
        self.assertIn('help_items', context)
        self.assertEqual(len(context['help_items']), 2)
        alice_help, bob_help = context['help_items']
        self.assertIsInstance(alice_help, Wrapper)
        self.assertEqual(alice_help.id, 'Alice')
        self.assertEqual(alice_help.label, 'Alice')
        self.assertEqual(alice_help.val, 'Beep')
        self.assertIsInstance(bob_help, Wrapper)
        self.assertEqual(bob_help.id, 'Bob')
        self.assertEqual(bob_help.label, 'BobLabel')
        self.assertEqual(bob_help.val, 'Boop')
        
        # Assert that for_context keeps items passed in via kwargs as they are (i.e. doesn't wrap them)
        instance = BaseHelpText()
        instance.help_items = ['Charlie', ('Dave', )]
        instance.__init__()
        context = instance.for_context(Charlie = 'This Is Charlie', Dave = 'And this is Dave')
        self.assertIn('help_items', context)
        self.assertIn('This Is Charlie', context['help_items'])
        self.assertIn('And this is Dave', context['help_items'])
        
class TestFormHelpText(FormTestCase):
    
    dummy_bases = (django_forms.Form, )
    dummy_attrs = {
        'alice': django_forms.CharField(label = 'Alice', help_text = 'Helptext for Alice'), 
        'bob': django_forms.CharField(label = 'Bob', help_text = 'Helptext for Bob'), 
    }
    
    def setUp(self):
        super().setUp()
        self.instance = FormHelpText(fields = {'alice': 'beep boop'})
        self.instance.form_class = self.get_dummy_form_class()
    
    def test_init_adds_fields(self):
        instance = FormHelpText(help_items = ['test'], fields = {'beep':'boop'})
        instance.__init__()
        self.assertIn('fields', instance.help_items)
        self.assertEqual(list(instance.help_items.keys()).index('fields'), 1)
        
    def test_field_helptexts(self):
        expected = [
            {'id': 'alice', 'label': 'Alice', 'text': 'beep boop'}, 
            {'id': 'bob', 'label': 'Bob', 'text': 'Helptext for Bob'}, 
        ]
        self.assertEqual(self.instance.field_helptexts, expected)
        
    def test_get_helptext_for_field(self):
        # Assert that get_helptext_for_field prioritizes helptexts declared in self.fields over formfield helptexts
        formfield_alice = django_forms.CharField(help_text = 'Helptext for Alice')
        ht_alice = self.instance.get_helptext_for_field('alice', formfield_alice)
        self.assertEqual(ht_alice, 'beep boop')
        
        formfield_bob = django_forms.CharField(help_text = 'Helptext for Bob')
        ht_bob = self.instance.get_helptext_for_field('bob', formfield_bob)
        self.assertEqual(ht_bob, 'Helptext for Bob')
        
        formfield_charlie = django_forms.CharField()
        ht_charlie = self.instance.get_helptext_for_field('charlie', formfield_charlie)
        self.assertEqual(ht_charlie, '')
        
    def test_for_context(self):
        context = self.instance.for_context()
        self.assertIn('help_items', context)
        help_items = []
        for i in context['help_items']:
            if isinstance(i, Wrapper):
                help_items.append(i.id)
        self.assertIn('fields', help_items)
        
class TestModelHelpText(AdminTestCase):
    
    dummy_bases = (django_forms.Form, )
    dummy_attrs = {
        'beschreibung': django_forms.CharField(label = 'Alice', help_text = 'Helptext for Alice'), 
        'bemerkungen': django_forms.CharField(label = 'Bob', help_text = 'Helptext for Bob'), 
    }
    
    model = artikel
    model_admin_class = ArtikelAdmin
    
    def setUp(self):
        super().setUp()
        request = self.get_request(path = '/admin/help/artikel/')
        self.instance = type('Dummy', (ModelHelpText, ), {'model':artikel})(request = request)
    
    def test_init(self):
        # Assert that init sets a missing help_title from the model's verbose name
        self.instance.help_title = ''
        self.instance.__init__(request = None)
        self.assertEqual(self.instance.help_title, 'Artikel')
        
        self.instance.help_title = 'Beep boop'
        self.instance.__init__(request = None)
        self.assertEqual(self.instance.help_title, 'Beep boop')
        
        # Assert that init sets the admin model 
        self.instance.model_admin = None
        self.instance.__init__(request = None)
        self.assertIsInstance(self.instance.model_admin, ArtikelAdmin)
        
        self.instance.__init__(request = None, model_admin = BuchAdmin(buch, miz_site))
        self.assertIsInstance(self.instance.model_admin, BuchAdmin)
        
        # Assert that init adds the inlines to the help_items
        help_items = self.instance.help_items
        self.assertIn('inlines', help_items)
        self.assertEqual(list(help_items.keys()).index('inlines'), len(help_items)-1)
    
    def test_inline_helptexts(self):
        # Assert that inline_helptexts uses an inline's verbose model attribute if present
        genre_inline_helptext = type('GenreHelpText', (ModelHelpText, ), {'model':genre, 'inline_text':'Genre Inline Text'})
        halp._registry = {'models':{genre:genre_inline_helptext}}
        expected = [
            {'id': 'inline-Genre', 'label': 'Genres', 'text': 'Genre Inline Text'}
        ]
        self.assertEqual(self.instance.inline_helptexts, expected)
        
    def test_get_helptext_for_field(self):
        # Assert that get_helptext_for_field takes a model field's help text if no help text for that field
        # is declared.
        self.assertEqual(
            self.instance.get_helptext_for_field('bemerkungen', None), 
            'Kommentare für Archiv-Mitarbeiter'
        )
        
        self.instance.fields['bemerkungen'] = 'Beep Boop'
        self.assertEqual(
            self.instance.get_helptext_for_field('bemerkungen', None), 
            'Beep Boop'
        )
