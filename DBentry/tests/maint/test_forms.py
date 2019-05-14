from ..base import MyTestCase
from ..mixins import CreateFormMixin

import DBentry.models as _models
from DBentry.maint.forms import get_dupe_fields_for_model

class TestDuplicatesFieldsForm(CreateFormMixin, MyTestCase):
        
    def test_get_dupefields_reverse_choices_are_grouped(self):
        # Assert that the reverse dupe fields are grouped by their related model.
        dupe_fields = get_dupe_fields_for_model(_models.musiker)
        self.assertIn('reverse', dupe_fields)
        reverse = dupe_fields['reverse']
        self.assertIsInstance(reverse, (list, tuple))
        
        # Get the group
        self.assertEqual(len(reverse), 1, msg = "There should be only reverse dupe fields group for musiker.")
        musiker_alias_group = reverse[0]
        self.assertIsInstance(musiker_alias_group, (list, tuple))
        
        # Get the group's name and choices
        self.assertEqual(len(musiker_alias_group), 2, msg = "Should have group name and group choices.")
        group_name, group_choices = musiker_alias_group
        self.assertIsInstance(group_name, str, msg = "Should be the group name.")
        self.assertIsInstance(group_choices, (list, tuple))
        
        # Get the choice's label and id
        self.assertEqual(len(group_choices), 1, msg = "Should only contain one tuple of choices.")
        choice = group_choices[0]
        self.assertIsInstance(choice, (list, tuple))
        self.assertEqual(len(choice), 2, msg = "Should be a two-tuple with label, id.")
        self.assertIsInstance(choice[0], str, msg = "Should be choice label.")
        self.assertIsInstance(choice[1], str, msg = "Should be choice id.")
        
    def test_get_dupefields_excludes_reverse_fk_field(self):
        # Assert that get_dupe_fields_for_model does not include the 'parent' ForeignKey field 
        # in its 'reverse' choices.
        dupe_fields = get_dupe_fields_for_model(_models.musiker)
        self.assertIn('reverse', dupe_fields)
        self.assertIn('Alias', dict(dupe_fields['reverse']))
        musiker_alias_fields = dict(dupe_fields['reverse'])['Alias']
        #TODO: this assertion will pass if ['parent','Parent'] is used or the structure of the choices is off (test above)
        self.assertNotIn(('parent', 'Parent'), musiker_alias_fields)
        
    def test_get_dupefields_sorts_reverse_choices(self):
        # Assert that get_dupe_fields_for_model sorts the reverse choices by 
        # - group name
        # - choice labels
        # ausgabe has the following 7 reverse rels:
        # [<ManyToOneRel: DBentry.bestand>, <ManyToOneRel: DBentry.ausgabe_jahr>, <ManyToOneRel: DBentry.ausgabe_lnum>, 
        # <ManyToOneRel: DBentry.artikel>, <ManyToOneRel: DBentry.basebrochure>, <ManyToOneRel: DBentry.ausgabe_num>, 
        # <ManyToOneRel: DBentry.ausgabe_monat>]
        dupe_fields = get_dupe_fields_for_model(_models.ausgabe)
        self.assertIn('reverse', dupe_fields)
        reverse = dupe_fields['reverse']
        self.assertEqual(len(reverse), 7)
        expected = ['Artikel', 'Ausgabe-Monat', 'Bestand', 'Jahr', 'Nummer', 'base brochure', 'lfd. Nummer']
        group_names = [group_name for group_name, group_choices in reverse]
        self.assertEqual(group_names, expected)
        
        
        
