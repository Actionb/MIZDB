from itertools import chain

from django.contrib.contenttypes.models import ContentType
from django.test import tag

from DBentry import utils, models as _models
from DBentry.factory import make
from DBentry.tests.base import RequestTestCase
from DBentry.tests.mixins import LoggingTestMixin, TestDataMixin
from DBentry.utils.models import (
    get_model_fields, get_model_relations, get_relation_info_to, get_updateable_fields
)


@tag('logging', 'merge')
class MergingTestCase(LoggingTestMixin, TestDataMixin, RequestTestCase):
    # RequestTestCase because a request object is needed to create LogEntries

    test_data_count = 3

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.original = cls.test_data[0]
        cls.merge_records = []
        for c, merge_record in enumerate(cls.test_data[1:], 1):
            setattr(cls, 'merge_record' + str(c), merge_record)
            cls.merge_records.append(merge_record)

    def setUp(self):
        super().setUp()
        self.request = self.get_request()
        self.ids = [self.original.pk]
        self.ids += [merge_record.pk for merge_record in self.merge_records]
        self.qs = self.model.objects.filter(pk__in=self.ids)
        # These are the related objects that belong to original:
        self.original_related = {}
        # These are the related objects that are affected by the merge and should
        # end up being related to original:
        self.merger_related = {}
        for rel in get_model_relations(self.model, forward=False):
            related_model, related_field = get_relation_info_to(self.model, rel)
            # These are the fields of the related_model that *should* retain their values:
            preserved_fields = [
                fld.attname
                for fld in get_model_fields(
                    related_model,
                    m2m=False,
                    exclude=[related_field.name],
                    primary_key=True
                )
            ]
            # The values of the objects of the related model that are related to original:
            self.original_related[(related_model, related_field)] = list(
                related_model.objects
                .filter(**{related_field.name: self.original})
                .values(*preserved_fields)
            )
            # A queryset of all objects of the related model affected by the merge
            updated_qs = related_model.objects.filter(
                **{related_field.name + '__in': self.merge_records})
            # The values of the objects in the aforementioned queryset
            self.merger_related[(related_model, related_field)] = list(
                updated_qs.values(*preserved_fields))

    def assertRestDeleted(self):
        # Assert whether the other records were deleted after the merge.
        qs = self.qs.exclude(pk=self.original.pk)
        if qs.exists():
            raise AssertionError(
                'Merged records were not deleted: {}'.format(str(qs)))
        self.deleted_records = self.merge_records  # prepare for the logging assertion

    def assertRestDeletedLogged(self):
        self.assertLoggedDeletion(getattr(self, 'deleted_records', []))

    def assertOriginalExpanded(self, expand_original=True):
        # Assert whether the original's values were expanded by the merged
        # records correctly.
        change_message_fields = set()
        # Get a list of field names of the original that are 'empty' and will be
        # updated by data from the other merged records:
        updateable_fields = get_updateable_fields(self.original)
        updateable_fields_other = set()
        for merge_record in self.merge_records:
            updateable_fields_other.update(get_updateable_fields(merge_record))
        original_value_dict = self.qs.filter(pk=self.original.pk).values()[0].items()
        for fld_name, value in original_value_dict:
            if expand_original and fld_name in updateable_fields:
                # Change possible, but ONLY if any other of the merged records
                # have values for these fields which is implied by that field's
                # name not showing up in their respective updateable_fields.
                if fld_name not in updateable_fields_other:
                    change_message_fields.add(fld_name)
                    expected_values = [
                        getattr(merge_record, fld_name)
                        for merge_record in self.merge_records
                    ]
                    if value not in expected_values:
                        raise AssertionError(
                            'Expected change did not occur: value of field {} '
                            'did not change. Expected possible values: {}'.format(
                                fld_name, str(expected_values)
                            )
                        )
            elif fld_name.startswith('_'):
                # A private field (possibly from ComputedNameModel). We cannot
                # ascertain (or rather: should not need to worry about) whether
                # this field's value should have changed or not.
                continue
            else:
                # No change expected since this field is not in updateable_fields
                old_value = getattr(self.original, fld_name)
                if old_value != value:
                    # A value has changed although it shouldn't have changed
                    raise AssertionError(
                        'Unexpected change with expand_original = {}: value of '
                        'field {} changed from {} to {}.'.format(
                            str(expand_original), fld_name, str(old_value), str(value)
                        )
                    )
        if change_message_fields:
            # prepare for the logging assertion:
            self.change_message_fields = change_message_fields

    def assertOriginalExpandedLogged(self):
        if getattr(self, 'change_message_fields', None):
            self.assertLoggedChange(
                self.original, fields=getattr(self, 'change_message_fields', []))

    def assertRelatedChanges(self):
        # Assert that the original is now related to all objects that were
        # related to the merge_records.
        added_rel_object = set()  # keeps track of every object that has been added to original
        for rel in get_model_relations(self.model, forward=False):
            related_model, related_field = get_relation_info_to(self.model, rel)
            if related_model == self.model:
                # ignore self relations
                continue
            pk_name = related_model._meta.pk.name
            pks_seen = set()
            # queryset of objects that are now related to original:
            qs = related_model.objects.filter(**{related_field.name: self.original})

            # objects added from the other merged records
            related_objects_added = self.merger_related.get(
                (related_model, related_field), [])
            for related_valdict in related_objects_added:
                rel_pk = related_valdict.pop(pk_name)
                pks_seen.add(rel_pk)
                if qs.filter(pk=rel_pk).count() != 1:
                    # UNIQUE CONSTRAINTS might have 'dropped' some duplicate
                    # related objects: look for an equivalent object.
                    equivalent_qs = qs.filter(**related_valdict)
                    c = equivalent_qs.count()
                    if c == 0:
                        # No equivalent objects are found in this set, we have
                        # lost data.
                        raise AssertionError(
                            'Relation-Change did not occur for related object'
                            ' {}:{}.'.format(
                                related_model._meta.model_name,
                                str(rel_pk)
                            )
                        )
                    elif c > 1:
                        # Multiple equivalent objects were found.
                        raise AssertionError(
                            'Multiple ({}) occurrences for related object '
                            '{}:{} found.'.format(
                                str(c),
                                related_model._meta.model_name,
                                str(rel_pk)
                            )
                        )
                    else:
                        added_rel_object.add(
                            ((related_model, related_field), equivalent_qs[0]))
                else:
                    added_rel_object.add(
                        ((related_model, related_field), qs.get(pk=rel_pk)))

            # objects that were already related to original
            already_related = self.original_related.get(
                (related_model, related_field), [])
            for related_valdict in already_related:
                rel_pk = related_valdict.pop(pk_name)
                pks_seen.add(rel_pk)
                if qs.filter(pk=rel_pk).count() != 1:
                    # UNIQUE CONSTRAINTS might have 'dropped' some duplicate
                    # related objects: look for an equivalent object.
                    equivalent_qs = qs.filter(**related_valdict)
                    c = equivalent_qs.count()
                    if c == 0:
                        # No equivalent objects are found in this set, we have lost data
                        raise AssertionError(
                            'A related object of the original was dropped '
                            'unexpectedly {}:{}.'.format(
                                related_model._meta.model_name,
                                str(rel_pk)
                            )
                        )
                    elif c > 1:
                        # Multiple equivalent objects were found
                        raise AssertionError(
                            'Multiple ({}) occurrences for related object '
                            '{}:{} found.'.format(
                                str(c),
                                related_model._meta.model_name,
                                str(rel_pk)
                            )
                        )

            unseen_qs = qs.exclude(pk__in=pks_seen)
            if unseen_qs.exists():
                # NEW related objects were added
                raise AssertionError(
                    'Unexpected additional {} relation-changes occurred: '
                    '{}'.format(
                        str(unseen_qs.count()), str(unseen_qs)
                    )
                )

        self.added_rel_object = added_rel_object

    def assertRelatedChangesLogged(self):
        # Assert that all changes/additions have been logged
        added_rel_object = getattr(self, 'added_rel_object', [])
        for (_related_model, related_field), related_obj in added_rel_object:
            try:
                self.assertLoggedAddition(self.original, related_obj)
            except AssertionError as e:
                raise e
            self.assertLoggedChange(
                related_obj, related_field.name, self.original)


# TODO: merge_record: most of the TestClasses for models are VERY basic
class MergeTestMethodsMixin(object):

    def test_merge_records_expand(self):
        # A merge with expanding the original's values.
        new_original, update_data = utils.merge_records(
            self.original,
            self.qs,
            expand_original=True,
            request=self.request
        )
        self.assertOriginalExpanded()
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertOriginalExpandedLogged()
        self.assertRelatedChangesLogged()
        self.assertRestDeletedLogged()

    def test_merge_records_no_expand(self):
        # A merge without expanding the original's values.
        new_original, update_data = utils.merge_records(
            self.original,
            self.qs,
            expand_original=False,
            request=self.request
        )
        self.assertOriginalExpanded(expand_original=False)
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertOriginalExpandedLogged()
        self.assertRelatedChangesLogged()
        self.assertRestDeletedLogged()


class TestMergingAusgabe(MergingTestCase):

    model = _models.Ausgabe
    test_data_count = 0

    @classmethod
    def setUpTestData(cls):
        default = {
            'ausgabejahr__extra': 1,
            'ausgabenum__extra': 1,
            'ausgabelnum__extra': 1,
            'ausgabemonat__extra': 1,
            'bestand__extra': 1
        }
        cls.obj1 = make(cls.model, **default)
        cls.obj2 = make(cls.model, beschreibung='Test', **default)
        cls.obj3 = make(cls.model, **default)
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        super().setUpTestData()

    def test_merge_records_expand(self):
        # A merge with expanding the original's values.
        new_original, update_data = utils.merge_records(
            self.original,
            self.qs,
            expand_original=True,
            request=self.request
        )
        self.assertOriginalExpanded()
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertEqual(
            new_original.beschreibung, self.merge_record1.beschreibung)

    def test_merge_records_no_expand(self):
        # A merge without expanding the original's values.
        new_original, update_data = utils.merge_records(
            self.original,
            self.qs,
            expand_original=False,
            request=self.request
        )
        self.assertOriginalExpanded(expand_original=False)
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertNotEqual(
            new_original.beschreibung, self.merge_record1.beschreibung)

    def test_merge_records_bestand_integrity(self):
        # Check that all bestände are accounted for in the new_original
        merge_records_bestand = [
            list(merge_record.bestand_set.all())
            for merge_record in self.merge_records
        ]
        all_bestand = list(self.original.bestand_set.all()) + list(
            chain(*merge_records_bestand))
        new_original, update_data = utils.merge_records(
            self.original,
            self.qs,
            expand_original=True,
            request=self.request
        )
        self.assertEqual(new_original.bestand_set.count(), len(all_bestand))
        for bestand_item in all_bestand:
            if bestand_item not in new_original.bestand_set.all():
                raise AssertionError(
                    'Bestand {} not found in new original.'.format(
                        str(bestand_item)
                    )
                )

    # The following test methods are rather tests for the assertions in MergingTestCase

    def test_merge_records_with_no_records_deleted(self):
        # The merge_records were not deleted after the merge, which,
        # technically, did not even happen.
        utils.merge_records(
            self.original,
            self.qs.none(),
            expand_original=False,
            request=self.request
        )
        with self.assertRaises(AssertionError) as context_manager:
            self.assertRestDeleted()
        self.assertTrue(context_manager.exception.args[0].startswith(
            'Merged records were not deleted:'))

    def test_merge_records_with_unexpected_change(self):
        # Original was expanded by an unexpected value.
        utils.merge_records(
            self.original,
            self.qs,
            expand_original=False,
            request=self.request
        )
        self.qs.filter(pk=self.original.pk).update(
            beschreibung='This should not happen.')
        with self.assertRaises(AssertionError) as context_manager:
            self.assertOriginalExpanded(expand_original=False)
        self.assertTrue(context_manager.exception.args[0].startswith(
            'Unexpected change with expand_original'))

    def test_merge_records_with_missing_relation_change(self):
        # Less related changes than expected.
        utils.merge_records(
            self.original,
            self.qs,
            expand_original=False,
            request=self.request
        )
        self.original.ausgabenum_set.all().delete()
        with self.assertRaises(AssertionError) as context_manager:
            self.assertRelatedChanges()
        self.assertTrue(context_manager.exception.args[0].startswith(
            'Relation-Change did not occur for related object'))

    def test_merge_records_with_additional_relation_change(self):
        # More related changes than expected
        utils.merge_records(
            self.original,
            self.qs,
            expand_original=False,
            request=self.request
        )
        make(_models.AusgabeNum, num=42, ausgabe=self.original)
        with self.assertRaises(AssertionError) as context_manager:
            self.assertRelatedChanges()
        self.assertTrue(context_manager.exception.args[0].startswith(
            'Unexpected additional 1 relation-changes occurred: '))


class TestMergingOrt(MergingTestCase, MergeTestMethodsMixin):
    model = _models.Ort


class TestMergingArtikel(MergingTestCase, MergeTestMethodsMixin):
    model = _models.Artikel


class TestMergingBand(MergingTestCase, MergeTestMethodsMixin):
    model = _models.Band


class TestMergingMusiker(MergingTestCase, MergeTestMethodsMixin):
    model = _models.Musiker


class TestMergingAudio(MergingTestCase, MergeTestMethodsMixin):
    model = _models.audio


class TestMergingAutor(MergingTestCase, MergeTestMethodsMixin):
    model = _models.Autor


class TestMergingGenre(MergingTestCase, MergeTestMethodsMixin):
    model = _models.Genre


class TestMergingSchlagwort(MergingTestCase, MergeTestMethodsMixin):
    model = _models.Schlagwort


class TestMergingMagazin(MergingTestCase, MergeTestMethodsMixin):

    model = _models.Magazin
    test_data_count = 0

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = cls.model.objects.create(magazin_name='Original-Magazin')
        cls.obj2 = cls.model.objects.create(magazin_name='Merger1-Magazin')
        cls.obj3 = cls.model.objects.create(magazin_name='Merger2-Magazin')
        cls.genre_original = _models.Genre.objects.create(genre='Original-Genre')
        cls.genre_merger1 = _models.Genre.objects.create(genre='Merger1-Genre')
        cls.genre_merger2 = _models.Genre.objects.create(genre='Merger2-Genre')
        cls.model.genre.through.objects.create(genre=cls.genre_original, magazin=cls.obj1)
        cls.model.genre.through.objects.create(genre=cls.genre_merger1, magazin=cls.obj2)
        cls.model.genre.through.objects.create(genre=cls.genre_merger2, magazin=cls.obj3)
        autor_instance = _models.Autor.objects.create(kuerzel='M1-Aut')
        cls.model.autor_set.through.objects.create(autor=autor_instance, magazin=cls.obj2)
        cls.ausgabe_original = _models.Ausgabe.objects.create(
            beschreibung='Original-Ausgabe', sonderausgabe=True, magazin=cls.obj1
        )
        cls.ausgabe_merger = _models.Ausgabe.objects.create(
            beschreibung='Merger1-Ausgabe', sonderausgabe=True, magazin=cls.obj2
        )

        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        super().setUpTestData()


class TestMergingPerson(MergingTestCase, MergeTestMethodsMixin):
    model = _models.Person


class VideoMergingDataMixin(object):

    model = _models.video
    test_data_count = 0

    @classmethod
    def setUpTestData(cls):
        obj1 = make(
            cls.model, titel='Original', tracks=3, band__extra=1,
            musiker__extra=1, bestand__extra=1,
        )
        cls.band_original = obj1.band.get()
        cls.musiker_original = obj1.musiker.get()
        cls.bestand_original = obj1.bestand_set.get()
        cls.obj1 = obj1

        obj2 = make(
            cls.model, titel='Merger1', tracks=3, band__extra=1,
            musiker__extra=1, bestand__extra=1,
        )
        cls.band_merger1 = obj2.band.get()
        cls.musiker_merger1 = obj2.musiker.get()
        cls.bestand_merger1 = obj2.bestand_set.get()
        cls.obj2 = obj2

        obj3 = make(
            cls.model, titel='Merger2', tracks=3, band__extra=1,
            musiker__extra=1, bestand__extra=1,
            beschreibung='Hello!'
        )
        cls.band_merger2 = obj3.band.get()
        cls.musiker_merger2 = obj3.musiker.get()
        cls.bestand_merger2 = obj3.bestand_set.get()
        cls.obj3 = obj3

        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        ContentType.objects.clear_cache()


class TestMergingVideoManual(VideoMergingDataMixin, MergingTestCase):

    def test_merge_records_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(
            self.original,
            self.qs,
            expand_original=True,
            request=self.request
        )
        self.assertEqual(new_original, self.obj1)
        self.assertEqual(new_original.titel, 'Original')
        self.assertEqual(new_original.tracks, 3)
        self.assertEqual(new_original.beschreibung, 'Hello!')

    def test_merge_records_no_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(
            self.original,
            self.qs,
            expand_original=False,
            request=self.request
        )
        self.assertEqual(new_original, self.obj1)
        self.assertEqual(new_original.titel, 'Original')
        self.assertEqual(new_original.tracks, 3)
        self.assertNotEqual(new_original.beschreibung, 'Hello!')

    def test_related_changes(self):
        new_original, update_data = utils.merge_records(
            self.original,
            self.qs,
            expand_original=False,
            request=self.request
        )
        self.assertIn(self.bestand_original, self.obj1.bestand_set.all())
        self.assertIn(self.bestand_merger1, self.obj1.bestand_set.all())
        self.assertIn(self.bestand_merger2, self.obj1.bestand_set.all())
        self.assertIn(self.musiker_original, self.obj1.musiker.all())
        self.assertIn(self.musiker_merger1, self.obj1.musiker.all())
        self.assertIn(self.musiker_merger2, self.obj1.musiker.all())
        self.assertIn(self.band_original, self.obj1.band.all())
        self.assertIn(self.band_merger1, self.obj1.band.all())
        self.assertIn(self.band_merger2, self.obj1.band.all())

    def test_rest_deleted(self):
        utils.merge_records(
            self.original,
            self.qs,
            expand_original=True,
            request=self.request
        )
        self.assertNotIn(self.obj2, self.model.objects.all())
        self.assertNotIn(self.obj3, self.model.objects.all())


# Using the more complex MergeTestMethodsMixin
class TestMergingVideo(VideoMergingDataMixin, MergingTestCase, MergeTestMethodsMixin):
    pass
