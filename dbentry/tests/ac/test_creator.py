from unittest.mock import Mock

import dbentry.models as _models
from dbentry.ac.creator import Creator, FailedObject, MultipleObjectsReturned
from dbentry.factory import make
from dbentry.tests.base import DataTestCase, mockv


class TestCreator(DataTestCase):
    model = _models.Autor

    @classmethod
    def setUpTestData(cls):
        cls.alice = make(_models.Person, vorname='Alice', nachname='Testman')
        cls.bob1 = make(_models.Person, vorname='Bob', nachname='Testman')
        cls.bob2 = make(_models.Person, vorname='Bob', nachname='Testman')
        cls.alice_autor = make(cls.model, person=cls.alice, kuerzel='AT')
        cls.bob1_autor = make(cls.model, person=cls.bob1, kuerzel='bob1')
        cls.bob2_autor = make(cls.model, person=cls.bob2, kuerzel='bob2')

        cls.test_data = [
            cls.alice, cls.alice_autor, cls.bob1, cls.bob2, cls.bob1_autor, cls.bob2_autor]

        super().setUpTestData()

    def test_create(self):
        creator = Creator(model=_models.Person)
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
        creator = Creator(model=_models.Datei)
        created = creator.create('text', preview=True)
        self.assertFalse(
            created,
            msg=(
                "create(preview = True: should return an empty dictionary if no "
                "creator function is set"
            )
        )

    def test_create_reraises_or_failed_object(self):
        creator = Creator(model=_models.Person, raise_exceptions=True)

        creator.creator = Mock(side_effect=MultipleObjectsReturned())
        msg = (
            "create(preview = False): MultipleObjectsReturned "
            "exceptions should bubble up"
        )
        with self.assertRaises(MultipleObjectsReturned, msg=msg):
            creator.create('Alice Testman', preview=False)

        creator.raise_exceptions = False
        msg = (
            "create(preview = False): No exceptions should bubble up if "
            "raise_exceptions == False"
        )
        with self.assertNotRaises(MultipleObjectsReturned, msg=msg):
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
        creator = Creator(model=_models.Person, raise_exceptions=False)
        self.assertEqual(
            creator.create('Bob Testman', preview=True), {},
            msg=(
                "create(preview = False): create preview should return an empty "
                "dict if multiple records in database fit the given parameters"
            )
        )
        creator.creator = mockv({'some': 'iterable'})
        self.assertEqual(creator.create('Bob Tester', preview=True), {'some': 'iterable'})

    def test_create_person(self):
        # return value is an OrderedDict with keys ('Vorname','Nachname','instance')
        creator = Creator(model=_models.Person)

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
            msg="create_person(preview = False): a Person instance is expected"
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
            msg="create_autor(preview = True): must return a Person instance"
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
            msg="create_autor(preview = False): must return a Person instance"
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

    def test_create_autor_no_person_pk(self):
        # Assert that create_autor does not filter on person.pk, but instead
        # on person.vorname and person.nachname.

        # BUG: The query to find matching Autor objects filtered on person.pk.
        # But the pk would be None for new, unsaved Person instances, which
        # means that query would also include Autor objects that have no
        # related Person (autor.person is None).

        p = make(_models.Person, vorname='Peter', nachname='Lustig')
        # make() would invent a kuerzel, so need to be explicit:
        a = make(_models.Autor, person=p, kuerzel='')
        p.delete()
        # a.person is now None, and any query for Autor with person.pk = None
        # would include it.
        creator = Creator(model=self.model)

        # Different name for the Autor, but the person.pk is the same as the
        # one from 'a'. Assert that create_autor doesn't return the wrong
        # Autor.
        created = creator.create_autor('Hermann Paschulke')
        self.assertNotEqual(created['instance'], a)
        self.assertNotEqual(created['instance'].person.nachname, 'Lustig')

    def test_create_autor_no_person_pk_multiple(self):
        # Same as above, but now there are multiple matching Autor objects for
        # person.pk = None.
        # Assert that we don't trigger a MultipleObjectsReturned exception.
        p = make(_models.Person, vorname='Peter', nachname='Lustig')
        # make() would invent a kuerzel, so need to be explicit:
        a = make(_models.Autor, person=p, kuerzel='')
        b = make(_models.Autor, person=p, kuerzel='')
        p.delete()
        creator = Creator(model=self.model)

        with self.assertNotRaises(MultipleObjectsReturned):
            created = creator.create_autor('Hermann Paschulke')
        self.assertNotEqual(created['instance'], a)
        self.assertNotEqual(created['instance'], b)
        self.assertNotEqual(created['instance'].person.nachname, 'Lustig')

    def test_create_autor_nachname_only(self):
        # Assert that create_autor creates a Person with just a surname, if
        # the text given consists of only one word.
        creator = Creator(model=self.model)
        created = creator.create_autor('Paschulke')
        self.assertEqual(created['Person']['Nachname'], 'Paschulke')
        self.assertEqual(created['instance'].person.nachname, 'Paschulke')

