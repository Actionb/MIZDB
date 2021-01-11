from itertools import chain
from django.core.exceptions import FieldDoesNotExist
from django.contrib.admin.utils import get_fields_from_path

import DBentry.models as _models
from DBentry.maint.forms import get_dupe_fields_for_model
from DBentry.tests.base import MyTestCase
from DBentry.tests.mixins import CreateFormMixin


class TestDuplicatesFieldsForm(CreateFormMixin, MyTestCase):

    def test_get_dupefields_reverse_choices_are_grouped(self):
        # Assert that the reverse dupe fields are grouped by their related model.
        dupe_fields = get_dupe_fields_for_model(_models.Musiker)
        self.assertIn('reverse', dupe_fields)
        reverse = dupe_fields['reverse']
        self.assertIsInstance(reverse, (list, tuple))

        # Get the group
        self.assertEqual(
            len(reverse), 1,
            msg="There should be only reverse dupe fields group for Musiker."
        )
        musiker_alias_group = reverse[0]
        self.assertIsInstance(musiker_alias_group, (list, tuple))

        # Get the group's name and choices
        self.assertEqual(
            len(musiker_alias_group), 2,
            msg="Should have group name and group choices."
        )
        group_name, group_choices = musiker_alias_group
        self.assertIsInstance(group_name, str, msg="Should be the group name.")
        self.assertIsInstance(group_choices, (list, tuple))

        # Get the choice's label and id
        self.assertEqual(
            len(group_choices), 1,
            msg="Should only contain one tuple of choices."
        )
        choice = group_choices[0]
        self.assertIsInstance(choice, (list, tuple))
        self.assertEqual(len(choice), 2, msg="Should be a two-tuple with label, id.")
        self.assertIsInstance(choice[0], str, msg="Should be choice label.")
        self.assertIsInstance(choice[1], str, msg="Should be choice id.")

    def test_get_dupefields_excludes_reverse_fk_field(self):
        # Assert that the reverse choices do not contain the ForeignKey field
        # of that reverse relation.
        dupe_fields = get_dupe_fields_for_model(_models.Musiker)
        self.assertIn('reverse', dupe_fields)
        self.assertIn('Alias', dict(dupe_fields['reverse']))
        musiker_alias_fields = dict(dupe_fields['reverse'])['Alias']
        self.assertNotIn('parent', [choice[0] for choice in musiker_alias_fields])

    def test_get_dupefields_sorts_reverse_choices(self):
        # Assert that get_dupe_fields_for_model sorts the reverse choices by
        # group name (lower()). ausgabe has the following 7 reverse rels:
        # <ManyToOneRel: DBentry.bestand>, <ManyToOneRel: DBentry.ausgabejahr>,
        # <ManyToOneRel: DBentry.ausgabelnum>, <ManyToOneRel: DBentry.artikel>,
        # <ManyToOneRel: DBentry.basebrochure>, <ManyToOneRel: DBentry.ausgabenum>,
        # <ManyToOneRel: DBentry.ausgabemonat>]
        dupe_fields = get_dupe_fields_for_model(_models.Ausgabe)
        self.assertIn('reverse', dupe_fields)
        reverse = dupe_fields['reverse']
        self.assertEqual(len(reverse), 7)
        expected = [
            'Artikel', 'Ausgabe-Monat', 'base brochure', 'Bestand', 'Jahr',
            'lfd. Nummer', 'Nummer'
        ]
        group_names = [group_name for group_name, group_choices in reverse]
        self.assertEqual(group_names, expected)

    def test_reverse_choices_are_queryable(self):
        # Assert that whatever is returned by get_dupe_fields_for_model can
        # actually be used in query.
        # Using get_fields_from_path to assert the ... queryability
        dupe_fields = get_dupe_fields_for_model(_models.Ausgabe)
        reverse = dupe_fields['reverse']
        all_choices = list(chain(
            *(group_choices for group_name, group_choices in reverse)
        ))
        failed = []
        for field_path, _label in all_choices:
            try:
                get_fields_from_path(_models.Ausgabe, field_path)
            except FieldDoesNotExist:
                failed.append(field_path)
        if failed:
            self.fail("Could not query for these fields:\n" + ", ".join(f for f in failed))
