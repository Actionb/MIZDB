
from collections import OrderedDict

from django.test import TestCase
from django.db import transaction

from DBentry.factory import modelfactory_factory
from DBentry.models import *

from .creator import Creator

class TestCreator(TestCase):
    
    empty_create_info = OrderedDict()
    
    @classmethod
    def setUpTestData(cls):
        cls.person_factory = modelfactory_factory(person)
        cls.autor_factory = modelfactory_factory(autor)
        cls.alice = person.objects.create(vorname='Alice', nachname='Testman')
        cls.bob1 = person.objects.create(vorname='Bob', nachname='Testman')
        cls.bob2 = person.objects.create(vorname='Bob', nachname='Testman')
        cls.alice_autor = autor.objects.create(person=cls.alice, kuerzel = 'al')
        cls.bob1_autor = autor.objects.create(person=cls.bob1, kuerzel = 'bob1')
        cls.bob2_autor = autor.objects.create(person=cls.bob2, kuerzel = 'bob2')
        
        #cls.test_data = [cls.alice, cls.bob1, cls.bob2]
        
    def test_create_person(self):
        self.assertFalse(person.objects.filter(vorname='Charlie', nachname='Testman').exists())
        definitely_new = 'Testman, Charlie'
        created = Creator(person, True).create_person(definitely_new, dry_run = False)
        self.assertIsNotNone(created.get('instance').pk)
        self.assertEqual(created.get('Vorname'), 'Charlie')
        self.assertEqual(created.get('Nachname'), 'Testman')
    
    def test_create_person_dry_run(self):
        # dry runs should never create (save) new records
        self.assertFalse(person.objects.filter(vorname='Charlie', nachname='Testman').exists())
        definitely_new = 'Testman, Charlie'
        created = Creator(person, True).create_person(definitely_new, dry_run = True)
        self.assertIsNone(created.get('instance').pk)
        self.assertEqual(created.get('Vorname'), 'Charlie')
        self.assertEqual(created.get('Nachname'), 'Testman')
        
    def test_createable_person(self):
        data = 'Testman, Alice'
        self.assertFalse(Creator(person, True).createable(data), 'createable should return False for existing objects')
        
        data = 'Testman, Bob'
        self.assertFalse(Creator(person, False).createable(data), 'createable should return False for multiple existing objects')
        
        data = 'Testman, Bob Alice'
        self.assertTrue(Creator(person, True).createable(data), 'createable should return True for new objects')
        
    def test_create_info_person(self):
        data = 'Testman, Alice'
        create_info = Creator(person, True).create_info(data)
        self.assertIn('Vorname', create_info)
        self.assertEqual(create_info.get('Vorname'), 'Alice')
        self.assertIn('Nachname', create_info)
        self.assertEqual(create_info.get('Nachname'), 'Testman')
        self.assertIn('instance', create_info)
        self.assertIsInstance(create_info.get('instance'), person)
        self.assertEqual(create_info.get('instance'), self.alice)
        
        # Multiple Bobs!
        data = 'Testman, Bob'
        create_info = Creator(person, True).create_info(data)
        self.assertEqual(create_info, self.empty_create_info)
        
        data = 'Testman, Bob Alice'
        create_info = Creator(person, True).create_info(data)
        self.assertIn('Vorname', create_info)
        self.assertEqual(create_info.get('Vorname'), 'Bob Alice')
        self.assertIn('Nachname', create_info)
        self.assertEqual(create_info.get('Nachname'), 'Testman')
        self.assertIn('instance', create_info)
        self.assertIsInstance(create_info.get('instance'), person)
        self.assertIsNone(create_info.get('instance').pk)
        
        
    def test_create_autor(self):
        self.assertFalse(autor.objects.filter(person__vorname='Charlie', person__nachname='Testman', kuerzel = 'CT').exists())
        definitely_new = 'Testman, Charlie (CT)'
        created = Creator(autor, True).create_autor(definitely_new, dry_run = False)
        self.assertIsNotNone(created.get('instance').pk)
        
        self.assertIn('Person', created)
        p = created.get('Person')
        self.assertIn('Vorname', p)
        self.assertEqual(p.get('Vorname'), 'Charlie')
        self.assertIn('Nachname', p)
        self.assertEqual(p.get('Nachname'), 'Testman')
        
        self.assertIn('Kürzel', created)
        self.assertEqual(created.get('Kürzel'), 'CT')
    
    def test_create_autor_dry_run(self):
        self.assertFalse(autor.objects.filter(person__vorname='Charlie', person__nachname='Testman', kuerzel = 'CT').exists())
        definitely_new = 'Testman, Charlie (CT)'
        created = Creator(autor, True).create_autor(definitely_new, dry_run = True)
        self.assertIsNone(created.get('instance').pk)
        
        self.assertIn('Person', created)
        p = created.get('Person')
        self.assertIsNone(p.get('instance').pk)
        
    def test_create_autor_create_info(self):
        # Existing autor
        data = 'Testman, Alice (al)'
        create_info = Creator(autor, True).create_info(data)
        
        self.assertIn('Person', create_info)
        p = create_info.get('Person')
        self.assertIn('Vorname', p)
        self.assertEqual(p.get('Vorname'), 'Alice')
        self.assertIn('Nachname', p)
        self.assertEqual(p.get('Nachname'), 'Testman')
        self.assertIn('instance', p)
        self.assertIsInstance(p.get('instance'), person)
        self.assertEqual(p.get('instance'), self.alice)
        
        self.assertIn('Kürzel', create_info)
        self.assertEqual(create_info.get('Kürzel'), 'al')
        self.assertIn('instance', create_info)
        self.assertEqual(create_info.get('instance'), self.alice_autor)
        
        # Multiple Bobs!
        data = 'Testman, Bob'
        create_info = Creator(autor, True).create_info(data)
        self.assertEqual(create_info, self.empty_create_info)
        data = 'Testman, Bob (BT)'
        create_info = Creator(autor, True).create_info(data)
        self.assertEqual(create_info, self.empty_create_info)
        
        
        # A new autor
        data = 'Testman, Bob Alice'
        create_info = Creator(autor, True).create_info(data)
        
        self.assertIn('Person', create_info)
        p = create_info.get('Person')
        self.assertIn('Vorname', p)
        self.assertEqual(p.get('Vorname'), 'Bob Alice')
        self.assertIn('Nachname', p)
        self.assertEqual(p.get('Nachname'), 'Testman')
        self.assertIn('instance', p)
        self.assertIsInstance(p.get('instance'), person)
        self.assertIsNone(p.get('instance').pk)
        
        self.assertIn('Kürzel', create_info)
        self.assertEqual(create_info.get('Kürzel'), '')
        self.assertIn('instance', create_info)
        self.assertIsNone(create_info.get('instance').pk)
        
    def test_createable_autor(self):
        data = 'Testman, Alice (al)'
        self.assertFalse(Creator(autor, True).createable(data), 'createable should return False for existing objects')
        
        data = 'Testman, Bob'
        self.assertFalse(Creator(autor, False).createable(data), 'createable should return False for multiple existing objects')
        
        data = 'Testman, Bob Alice'
        self.assertTrue(Creator(autor, True).createable(data), 'createable should return True for new objects')
