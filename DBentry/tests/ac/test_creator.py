
from ..base import DataTestCase, mockv, mockex

import DBentry.models as _models
from DBentry.factory import make
from DBentry.ac.creator import Creator, MultipleObjectsReturnedException, FailedObject


class TestCreator(DataTestCase):
    model = _models.autor

    @classmethod
    def setUpTestData(cls):
        cls.alice = make(_models.person, vorname='Alice', nachname='Testman')
        cls.bob1 = make(_models.person, vorname='Bob', nachname='Testman')
        cls.bob2 = make(_models.person, vorname='Bob', nachname='Testman')
        cls.alice_autor = make(cls.model, person=cls.alice, kuerzel='AT')
        cls.bob1_autor = make(cls.model, person=cls.bob1, kuerzel='bob1')
        cls.bob2_autor = make(cls.model, person=cls.bob2, kuerzel='bob2')

        cls.test_data = [
            cls.alice, cls.alice_autor, cls.bob1, cls.bob2, cls.bob1_autor, cls.bob2_autor]

        super().setUpTestData()

    def test_create(self):
        creator = Creator(model=_models.person)
        created = creator.create('Charlie Testman', preview=False)
        self.assertIn('instance', created)
        self.assertIsNotNone(
            created['instance'],
            msg="create(preview = False): returned dict must contain a model instance"
        )
        self.assertIsNotNone(
            created['instance'].pk,
            msg="create(preview = False): must return a saved instance"
        )
        self.assertEqual(created['instance'].vorname, 'Charlie')
        self.assertEqual(created['instance'].nachname, 'Testman')

    def test_create_creator_func_is_none(self):
        creator = Creator(model=_models.datei)
        created = creator.create('text', preview=True)
        self.assertFalse(
            created,
            msg=(
                "create(preview = True: should return an empty dictionary if no "
                "creator function is set"
            )
        )

    def test_create_reraises_or_failed_object(self):
        creator = Creator(model=_models.person, raise_exceptions=True)

        creator.creator = mockex(MultipleObjectsReturnedException())
        msg = (
            "create(preview = False): MultipleObjectsReturnedException "
            "exceptions should bubble up"
        )
        with self.assertRaises(MultipleObjectsReturnedException, msg=msg):
            creator.create('Alice Testman', preview=False)

        creator.raise_exceptions = False
        msg = (
            "create(preview = False): No exceptions should bubble up if "
            "raise_exceptions == False"
        )
        with self.assertNotRaises(MultipleObjectsReturnedException, msg=msg):
            created = creator.create('Alice Testman', False)
            self.assertIn('instance', created)
            self.assertIsInstance(
                created['instance'], FailedObject,
                msg=(
                    "create(preview = False): Error handling should have returned "
                    "a FailedObject instance"
                )
            )

    def test_create_preview(self):
        creator = Creator(model=_models.person, raise_exceptions=False)
        self.assertEqual(
            creator.create('Bob Testman', preview=True), {},
            msg=(
                "create(preview = False): create preview should return an empty "
                "dict if multiple records in database fit the given parameters"
            )
        )
        creator.creator = mockv({'some': 'iterable'})
        self.assertEqual(creator.create('Bob Tester', preview=True), {'some': 'iterable'})

    def test_get_model_instance(self):
        # _get_model_instance should return a new unsaved model object if no matches are found
        creator = Creator(model=_models.person)
        inst = creator._get_model_instance(_models.person, nachname='Nobody')
        self.assertIsInstance(inst, _models.person)
        self.assertIsNone(inst.pk)
        self.assertEqual(inst.nachname, 'Nobody')

        # _get_model_instance should return an existing model object if there is only one match
        alice_data = dict(vorname='Alice', nachname='Testman')
        inst = creator._get_model_instance(_models.person, **alice_data)
        self.assertEqual(inst, self.alice)

        # _get_model_instance should raise a
        # MultipleObjectsReturnedException if there is more than one match
        bob_data = dict(vorname='Bob', nachname='Testman')
        with self.assertRaises(MultipleObjectsReturnedException):
            creator._get_model_instance(_models.person, **bob_data)

    def test_create_person(self):
        # return value is an OrderedDict with keys ('Vorname','Nachname','instance')
        creator = Creator(model=_models.person)

        created = creator.create_person('Bob Tester', preview=True)
        self.assertIn(
            'Vorname', created,
            msg="create_person(preview = True): a Vorname key is expected"
        )
        self.assertEqual(created['Vorname'], 'Bob')
        self.assertIn(
            'Nachname', created,
            msg="create_person(preview = True): a Nachname key is expected"
        )
        self.assertEqual(created['Nachname'], 'Tester')
        self.assertIn('instance', created)
        self.assertIsNotNone(
            created['instance'],
            msg="create_person(preview = True): must return an instance"
        )
        self.assertIsNone(
            created['instance'].pk,
            msg="create_person(preview = True): must return an unsaved instance"
        )

        created = creator.create_person('Bob Tester', preview=False)
        self.assertIn(
            'Vorname', created,
            msg="create_person(preview = False): a Vorname key is expected"
        )
        self.assertEqual(created['Vorname'], 'Bob')
        self.assertIn(
            'Nachname', created,
            msg="create_person(preview = False): a Nachname key is expected"
        )
        self.assertEqual(created['Nachname'], 'Tester')
        self.assertIn('instance', created)
        self.assertIsNotNone(
            created['instance'],
            msg="create_person(preview = False): a person instance is expected"
        )
        self.assertIsNotNone(
            created['instance'].pk,
            "create_person(preview = False): must return a saved instance"
        )
        self.assertEqual(created['instance'].vorname, 'Bob')
        self.assertEqual(created['instance'].nachname, 'Tester')

    def test_create_autor(self):
        # return value is an OrderedDict with keys ('Person','Kürzel','instance')
        creator = Creator(model=self.model)

        created = creator.create_autor('Bob Tester(BT)', preview=True)
        self.assertIn(
            'Person', created,
            msg="create_autor(preview = True): a Person key is expected"
        )
        self.assertIn('Vorname', created['Person'])
        self.assertEqual(created['Person']['Vorname'], 'Bob')
        self.assertIn('Nachname', created['Person'])
        self.assertEqual(created['Person']['Nachname'], 'Tester')
        self.assertIn('instance', created['Person'])
        self.assertIsNotNone(
            created['Person']['instance'],
            msg="create_autor(preview = True): must return a person instance"
        )
        self.assertIsNone(
            created['Person']['instance'].pk,
            msg="create_autor(preview = True): must return an unsaved instance"
        )
        self.assertIn(
            'Kürzel', created,
            msg="create_autor(preview = True): a Kürzel key is expected"
        )

        created = creator.create_autor('Bob Tester(BT)', preview=False)
        self.assertIn(
            'Person', created,
            msg="create_autor(preview = False): a Person key is expected"
        )
        self.assertIn('Vorname', created['Person'])
        self.assertEqual(created['Person']['Vorname'], 'Bob')
        self.assertIn('Nachname', created['Person'])
        self.assertEqual(created['Person']['Nachname'], 'Tester')
        self.assertIn('instance', created['Person'])
        self.assertIsNotNone(
            created['Person']['instance'],
            msg="create_autor(preview = False): must return a person instance"
        )
        self.assertIn(
            'Kürzel', created,
            msg="create_autor(preview = False): a Kürzel key is expected"
        )

        self.assertEqual(created['Kürzel'], 'BT')
        self.assertIn('instance', created)
        self.assertIsNotNone(
            created['instance'],
            msg="create_autor(preview = False): must return an autor instance"
        )
        self.assertIsNotNone(
            created['instance'].pk,
            "create_autor(preview = False): must return a saved instance"
        )
        self.assertEqual(created['instance'].person, created['Person']['instance'])
        self.assertEqual(created['instance'].kuerzel, 'BT')

        # Assert that create_autor uses an existing person object to find a
        # matching autor object:
        creator.create_person = mockv({'instance': self.alice})
        creator._get_model_instance = mockv(self.alice_autor)
        created = creator.create_autor('Not Important (NI)', False)
        creator._get_model_instance.assert_called_with(
            self.model, person=self.alice, kuerzel='NI')
        self.assertEqual(created['instance'], self.alice_autor)
