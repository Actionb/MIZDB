from .base import *

from DBentry.ac.creator import *


class TestCreator(DataTestCase):
    model = autor
    raw_data = [
        {'person__vorname':'Alice', 'person__nachname':'Testman', 'kuerzel':'AT'}
    ]
    
    def assertToReraiseOrNotToReraise(self, creator, method_name):
        """
        Assert that the method reraises exceptions according to creator.raise_exceptions.
        """
        x = creator.raise_exceptions
        
        method = getattr(creator, method_name)
        creator.raise_exceptions = False
        creator.creator = mockex(MultipleObjectsReturnedException())
        with self.assertNotRaises(MultipleObjectsReturnedException):
            method('Alice Testman')
        creator.raise_exceptions = True
        with self.assertRaises(MultipleObjectsReturnedException):
            method('Alice Testman')
            
        creator.raise_exceptions = x # restore the old value
    
    def test_init_creator_func_returns_none(self):
        # attribute 'creator' should be set to a function that returns none if the instance has no method called
        # 'create_{model_name}'.
        creator = Creator(model = datei)
        self.assertIn('lambda', str(creator.creator)) # defaults to a lambda function
        # Test random arguments to 'verify' that it returns None
        self.assertIsNone(creator.creator(1, True))
        self.assertIsNone(creator.creator('beep', 'boop'))
        
    def test_create_reraises_or_failed_object(self):
        # If self.raise_exceptions, MultipleObjectsReturnedException exceptions should bubble up
        creator = Creator(model = person, raise_exceptions = True)
            
        creator.creator = mockex(MultipleObjectsReturnedException())
        with self.assertRaises(MultipleObjectsReturnedException):
            creator.create('Alice Testman')
            
        # If not self.raise_exceptions, a failed object should be returned
        creator.raise_exceptions = False
        with self.assertNotRaises(MultipleObjectsReturnedException):
            created = creator.create('Alice Testman')
        self.assertIsInstance(created, FailedObject)
    
    def test_createable(self):
        # createable should return True if no records match string 'text' and no exceptions occured
        creator = Creator(model = person, raise_exceptions = True)
        creator.creator = mockv(True)
        self.assertTrue(creator.createable('Bob Tester'))
        
        # createable should return False if an existing matching record was found
        creator.creator = mockv(OrderedDict([('instance', self.obj1)]))
        self.assertEqual(creator.createable('Alice Testman'), False)
        
        # createable should either return False or reraise upon encountering an exception, depending on raise_exceptions
        self.assertToReraiseOrNotToReraise(creator, 'createable')
        creator.raise_exceptions = False
        
        creator.creator = mockex(MultipleObjectsReturnedException())
        self.assertEqual(creator.createable('Alice Testman'), False)
        
    def test_create_info_reraises(self):
        self.assertToReraiseOrNotToReraise(Creator(person, True), 'create_info')
        
    def test_get_model_instance(self):
        # _get_model_instance should return a new unsaved model object if no matches are found
        creator = Creator(model = person)
        inst = creator._get_model_instance(person, nachname = 'Nobody')
        self.assertIsInstance(inst, person)
        self.assertIsNone(inst.pk)
        self.assertEqual(inst.nachname, 'Nobody')
        
        # _get_model_instance should return an existing model object if there is only one match
        alice_data = dict(vorname = 'Alice', nachname = 'Testman')
        inst = creator._get_model_instance(person, **alice_data)
        self.assertEqual(inst, self.obj1.person)
        
        # _get_model_instance should raise a MultipleObjectsReturnedException if there is more than one match
        make(person, **alice_data)
        with self.assertRaises(MultipleObjectsReturnedException):
            creator._get_model_instance(person, **alice_data)
        
    def test_create_person(self):
        # return value is an OrderedDict with keys ('Vorname','Nachname','instance')
        
        # Assert that create_person only saves a new instance and only if not dry_run
        creator = Creator(model = person)
        created = creator.create_person('Bob Tester', dry_run = True)
        self.assertIsNone(created['instance'].pk)
        
        created = creator.create_person('Bob Tester', dry_run = False)
        self.assertIsNotNone(created['instance'].pk)
        
    def test_create_autor(self):
        # return value is an OrderedDict with keys ('Person','Kürzel','instance')
        creator = Creator(model = autor)
        
        # Assert that create_autor uses an existing person object to find a matching autor object
        creator.create_person = mockv({'instance' : self.obj1.person})
        creator._get_model_instance = mockv(self.obj1)
        created = creator.create_autor('Not Important (NI)')
        creator._get_model_instance.assert_called_with(autor, person = self.obj1.person, kuerzel = 'NI')
        self.assertEqual(created['instance'], self.obj1)
        
        # Assert that create_autor does not save model objects during a dry run
        creator.create_person = mockv({'instance' : person(vorname = 'Bob', nachname = 'Testman')})
        created = creator.create_autor('Bob Testman (BT)', dry_run = True)
        self.assertIsNone(created['instance'].pk)
        self.assertIsNone(created['instance'].person.pk)
        
        created = creator.create_autor('Bob Testman (BT)', dry_run = False)
        self.assertIsNotNone(created['instance'].pk)
        self.assertIsNotNone(created['instance'].person.pk)
        

class TestCreatorFunctional(TestCase):
    
    empty_create_info = OrderedDict()
    
    @classmethod
    def setUpTestData(cls):
        cls.alice = make(person, vorname='Alice', nachname='Testman')
        cls.bob1 = make(person, vorname='Bob', nachname='Testman')
        cls.bob2 = make(person, vorname='Bob', nachname='Testman')
        cls.alice_autor = make(autor, person=cls.alice, kuerzel = 'al')
        cls.bob1_autor = make(autor, person=cls.bob1, kuerzel = 'bob1')
        cls.bob2_autor = make(autor, person=cls.bob2, kuerzel = 'bob2')
        
    def test_create_person(self):
        self.assertFalse(person.objects.filter(vorname='Charlie', nachname='Testman').exists())
        definitely_new = 'Testman, Charlie'
        created = Creator(person, True).create_person(definitely_new, dry_run = False)
        instance = created.get('instance')
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.vorname, 'Charlie')        
        self.assertEqual(instance.nachname, 'Testman')
        self.assertEqual(created.get('Vorname'), 'Charlie')
        self.assertEqual(created.get('Nachname'), 'Testman')
    
    def test_create_person_dry_run(self):
        # dry runs should never create (save) new records
        self.assertFalse(person.objects.filter(vorname='Charlie', nachname='Testman').exists())
        definitely_new = 'Testman, Charlie'
        created = Creator(person, True).create_person(definitely_new, dry_run = True)
        instance = created.get('instance')
        self.assertIsNone(instance.pk)
        self.assertEqual(instance.vorname, 'Charlie')        
        self.assertEqual(instance.nachname, 'Testman')
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
        create_info = Creator(person, False).create_info(data)
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
        
        # autor
        self.assertIsNotNone(created.get('instance').pk)
        self.assertIn('Kürzel', created)
        self.assertEqual(created.get('Kürzel'), 'CT')
        
        # autor.person
        self.assertIn('Person', created)
        p = created.get('Person')
        self.assertIn('Vorname', p)
        self.assertEqual(p.get('Vorname'), 'Charlie')
        self.assertIn('Nachname', p)
        self.assertEqual(p.get('Nachname'), 'Testman')
        self.assertIn('instance', p)
        instance = p.get('instance')
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.vorname, 'Charlie')
        self.assertEqual(instance.nachname, 'Testman')
        
        # Assert that create_autor reuses an existing person record if applicable
        created = Creator(autor, True).create_autor('Alice Testman (XY)')
        self.assertIn('Person', created)
        self.assertIn('instance', created.get('Person'))
        self.assertEqual(created.get('Person').get('instance'), self.alice)
    
    def test_create_autor_dry_run(self):
        self.assertFalse(autor.objects.filter(person__vorname='Charlie', person__nachname='Testman', kuerzel = 'CT').exists())
        definitely_new = 'Testman, Charlie (CT)'
        created = Creator(autor, True).create_autor(definitely_new, dry_run = True)
        self.assertIsNone(created.get('instance').pk)
        
        self.assertIn('Person', created)
        p = created.get('Person')
        self.assertIsNone(p.get('instance').pk)
        
    def test_create_info_autor(self):
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
        create_info = Creator(autor, False).create_info(data)
        self.assertEqual(create_info, self.empty_create_info)
        data = 'Testman, Bob (BT)'
        create_info = Creator(autor, False).create_info(data)
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
