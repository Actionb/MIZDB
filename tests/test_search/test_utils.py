from django.core import exceptions
from django.db.models.constants import LOOKUP_SEP

from dbentry.search import utils
from tests.case import MIZTestCase

from .models import Artikel, Ausgabe, Magazin


class TestUtils(MIZTestCase):

    def test_get_dbfield_from_path(self):
        test_data = [
            (
                Artikel, 'seite__gt',
                (Artikel._meta.get_field('seite'), ['gt'])
            ),
            (
                Artikel, 'ausgabe__magazin__magazin_name__icontains',
                (Magazin._meta.get_field('magazin_name'), ['icontains'])
            ),
            (
                Ausgabe, 'e_datum__year__gte',
                (Ausgabe._meta.get_field('e_datum'), ['year', 'gte'])
            )
        ]
        for model, path, expected in test_data:
            with self.subTest(path=path):
                self.assertEqual(utils.get_dbfield_from_path(model, path), expected)

    def test_get_dbfield_from_path_fielderror_on_reverse_relation(self):
        """
        Assert that get_dbfield_from_path raises a FieldError exception, if the
        field path resolves to a reverse relation object.
        """
        with self.assertRaises(exceptions.FieldError) as cm:
            utils.get_dbfield_from_path(Magazin, 'ausgaben__artikel')
        self.assertEqual(cm.exception.args[0], "Reverse relations not supported.")

    def test_get_dbfield_from_path_fielddoesnotexist_on_invalid_path(self):
        """
        Assert that get_dbfield_from_path raises a FieldDoesNotExist exception,
        if the field path is invalid for the given model.
        """
        with self.assertRaises(exceptions.FieldDoesNotExist):
            utils.get_dbfield_from_path(Ausgabe, 'not__a__valid__path')

    def test_get_dbfield_from_path_fielderror_on_invalid_lookup(self):
        """
        Assert that get_dbfield_from_path raises a FieldError exception,
        if the path contains an invalid lookup.
        """
        with self.assertRaises(exceptions.FieldError):
            utils.get_dbfield_from_path(Ausgabe, 'magazin__icontains')

    def test_strip_lookups_from_path(self):
        """Assert that strip_lookups_from_path strips the given lookups from a path."""
        test_data = [
            # lookup, path, expected result
            (['in'], 'datum__jahr__in', 'datum__jahr'),
            (['foo', 'bar'], 'foo__bar__foo', 'foo'),
            (['foo'], 'foo', 'foo')
        ]
        for lookups, path, expected in test_data:
            with self.subTest(lookup=lookups, path=path):
                self.assertEqual(utils.strip_lookups_from_path(path, lookups), expected)
                self.assertNotIn(
                    f"{LOOKUP_SEP}{lookups}", utils.strip_lookups_from_path(path, lookups)
                )
