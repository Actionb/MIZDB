from .base import *

from django import forms as django_forms

from DBentry.help.helptext import formfield_to_modelfield, HTMLWrapper, BaseHelpText, ModelAdminHelpText, FormViewHelpText

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
        wrapped = HTMLWrapper(id = 'test', val = 'beep boop')
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
        wrapped = HTMLWrapper(id = 'test', val = 'beep boop')
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
        helptext_instance = BaseHelpText()
        helptext_instance.Alice = None
        helptext_instance.help_items = ['Alice']
        helptext_instance.__init__()
        context = helptext_instance.for_context()
        self.assertIn('help_items', context)
        self.assertFalse(context['help_items'])
        
        # Assert that for_context accepts a 'help_item' of type str
        helptext_instance = BaseHelpText()
        helptext_instance.Alice = 'Beep'
        helptext_instance.help_items = ['Alice']
        helptext_instance.__init__()
        context = helptext_instance.for_context()
        self.assertIn('help_items', context)
        self.assertEqual(len(context['help_items']), 1)
        alice_help = context['help_items'][0]
        self.assertIsInstance(alice_help, HTMLWrapper)
        self.assertEqual(alice_help.id, 'Alice')
        self.assertEqual(alice_help.label, 'Alice')
        self.assertEqual(alice_help.val, 'Beep')
        
        # Assert that for_context accepts a help_item of type list/tuple
        helptext_instance = BaseHelpText()
        helptext_instance.Alice = 'Beep'
        helptext_instance.Bob = 'Boop'
        helptext_instance.help_items = [('Alice', ), ['Bob', 'BobLabel']]
        helptext_instance.__init__()
        context = helptext_instance.for_context()
        self.assertIn('help_items', context)
        self.assertEqual(len(context['help_items']), 2)
        alice_help, bob_help = context['help_items']
        self.assertIsInstance(alice_help, HTMLWrapper)
        self.assertEqual(alice_help.id, 'Alice')
        self.assertEqual(alice_help.label, 'Alice')
        self.assertEqual(alice_help.val, 'Beep')
        self.assertIsInstance(bob_help, HTMLWrapper)
        self.assertEqual(bob_help.id, 'Bob')
        self.assertEqual(bob_help.label, 'BobLabel')
        self.assertEqual(bob_help.val, 'Boop')
        
        # Assert that for_context keeps items passed in via kwargs as they are (i.e. doesn't wrap them)
        helptext_instance = BaseHelpText()
        helptext_instance.help_items = ['Charlie', ('Dave', )]
        helptext_instance.__init__()
        context = helptext_instance.for_context(Charlie = 'This Is Charlie', Dave = 'And this is Dave')
        self.assertIn('help_items', context)
        self.assertIn('This Is Charlie', context['help_items'])
        self.assertIn('And this is Dave', context['help_items'])
        
        # Assert that for_context adds site_title and breadcrumbs_title
        helptext_instance = BaseHelpText()
        helptext_instance.site_title = 'Beep'
        helptext_instance.breadcrumbs_title = 'Boop'
        context = helptext_instance.for_context()
        self.assertIn('site_title', context)
        self.assertEqual(context['site_title'], 'Beep')
        self.assertIn('breadcrumbs_title', context)
        self.assertEqual(context['breadcrumbs_title'], 'Boop')
        
        
class TestFormViewHelpText(FormViewHelpTextMixin, FormTestCase):
    
    dummy_bases = (django_forms.Form, )
    dummy_attrs = {
        'alice': django_forms.CharField(label = 'Alice', help_text = 'Helptext for Alice'), 
        'bob': django_forms.CharField(label = 'Bob', help_text = 'Helptext for Bob'), 
    }
    helptext_class = FormViewHelpText
    
    def get_helptext_initkwargs(self):
        # Default the initkwargs to fields = {'alice': 'beep boop'}
        return {'fields': {'alice': 'beep boop'}}
    
    def test_init_adds_fields(self):
        # Assert that init adds 'fields' to the help_items as the second item if help_items has at least one item
        helptext_instance = self.get_helptext_instance()
        self.assertIn('fields', helptext_instance.help_items)
        self.assertEqual(list(helptext_instance.help_items.keys()).index('fields'), 0)
        
        helptext_instance = self.get_helptext_instance(help_items = ['test'])
        self.assertIn('fields', helptext_instance.help_items)
        help_item_keys = list(helptext_instance.help_items.keys())
        self.assertEqual(help_item_keys.index('fields'), 1)
        
        helptext_instance = self.get_helptext_instance(help_items = ['test', 'bla', 'jada'], fields = {'beep':'boop'})
        self.assertIn('fields', helptext_instance.help_items)
        help_item_keys = list(helptext_instance.help_items.keys())
        self.assertEqual(help_item_keys.index('test'), 0)
        self.assertEqual(help_item_keys.index('fields'), 1)
        self.assertEqual(help_item_keys.index('bla'), 2)
        self.assertEqual(help_item_keys.index('jada'), 3)
        
    def test_field_helptexts(self):
        expected = [
            {'id': 'alice', 'label': 'Alice', 'text': 'beep boop'}, 
            {'id': 'bob', 'label': 'Bob', 'text': 'Helptext for Bob'}, 
        ]
        self.assertEqual(self.get_helptext_instance().field_helptexts, expected)
        
    def test_get_helptext_for_field(self):
        # Assert that get_helptext_for_field prioritizes helptexts declared in self.fields over formfield helptexts
        helptext_instance = self.get_helptext_instance()
        
        formfield_alice = django_forms.CharField(help_text = 'Helptext for Alice')
        ht_alice = helptext_instance.get_helptext_for_field('alice', formfield_alice)
        self.assertEqual(ht_alice, 'beep boop')
        
        formfield_bob = django_forms.CharField(help_text = 'Helptext for Bob')
        ht_bob = helptext_instance.get_helptext_for_field('bob', formfield_bob)
        self.assertEqual(ht_bob, 'Helptext for Bob')
        
        formfield_charlie = django_forms.CharField()
        ht_charlie = helptext_instance.get_helptext_for_field('charlie', formfield_charlie)
        self.assertEqual(ht_charlie, '')
        
    def test_for_context(self):
        context = self.get_helptext_instance().for_context()
        self.assertIn('help_items', context)
        help_items = []
        for i in context['help_items']:
            if isinstance(i, HTMLWrapper):
                help_items.append(i.id)
        self.assertIn('fields', help_items)
        
class TestModelAdminHelpText(ModelAdminHelpTextTestCase):
    
    path = '/admin/help/artikel/'
    
    helptext_class = type('Dummy', (ModelAdminHelpText, ), {'model':artikel})
    
    def test_init(self):
        helptext_instance = self.get_helptext_instance()
        minimal_initkwargs = {'request':None, 'registry':None} # we do not need the full initkwargs to test the init method
        
        # Assert that init sets a missing index_title from the model's verbose name
        helptext_instance.index_title = ''
        helptext_instance.__init__(**minimal_initkwargs)
        self.assertEqual(helptext_instance.index_title, 'Artikel')
        
        helptext_instance.index_title = 'Beep boop'
        helptext_instance.__init__(**minimal_initkwargs)
        self.assertEqual(helptext_instance.index_title, 'Beep boop')
        
        # Assert that init sets the admin model 
        helptext_instance.model_admin = None
        helptext_instance.__init__(**minimal_initkwargs)
        self.assertIsInstance(helptext_instance.model_admin, ArtikelAdmin)
        
        helptext_instance.__init__(model_admin = BuchAdmin(buch, miz_site), **minimal_initkwargs)
        self.assertIsInstance(helptext_instance.model_admin, BuchAdmin)
        
        # Assert that init adds the inlines to the help_items, if there is at least one inline
        help_items = helptext_instance.help_items
        self.assertNotIn('inlines', help_items)
        
        helptext_instance.inlines = ['just pretend']
        helptext_instance.__init__(**minimal_initkwargs)
        help_items = helptext_instance.help_items
        self.assertIn('inlines', help_items)
        self.assertEqual(list(help_items.keys()).index('inlines'), len(help_items)-1)
    
    def test_inline_helptexts(self):
        # Assert that inline_helptexts uses an inline's verbose model attribute if present
        genre_inline_helptext = type('GenreHelpText', (ModelAdminHelpText, ), {'model':genre, 'inline_text':'Genre Inline Text'})
        self.registry.register(genre_inline_helptext, None)
        expected = [
            {'id': 'inline-Genre', 'label': 'Genres', 'text': 'Genre Inline Text'}
        ]
        self.assertEqual(self.get_helptext_instance().inline_helptexts, expected)
        
    def test_get_helptext_for_field(self):
        # Assert that get_helptext_for_field takes a model field's help text if no help text for that field
        # is declared.
        helptext_instance = self.get_helptext_instance()
        
        self.assertEqual(
            helptext_instance.get_helptext_for_field('bemerkungen', None), 
            'Kommentare für Archiv-Mitarbeiter'
        )
        
        helptext_instance.fields['bemerkungen'] = 'Beep Boop'
        self.assertEqual(
            helptext_instance.get_helptext_for_field('bemerkungen', None), 
            'Beep Boop'
        )
