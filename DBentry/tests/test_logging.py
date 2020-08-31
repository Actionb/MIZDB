from .base import ViewTestCase

from django import views
from django.utils.encoding import force_text
from django.utils.text import capfirst
from django.utils.translation import override as translation_override

import DBentry.models as _models
from DBentry.logging import LoggingMixin, ADDITION, CHANGE, DELETION, get_logger
from DBentry.factory import make


class TestLoggingMixin(ViewTestCase):

    model = _models.Band
    view_bases = (LoggingMixin, views.View)

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, genre__genre='Related')
        cls.obj2 = make(cls.model, band_name='Testband', beschreibung='This is a test.')
        cls.m2m = cls.model.genre.through.objects.get(band=cls.obj1)

        cls.ort = make(_models.Ort)

        cls.test_data = [cls.obj1, cls.obj2, cls.m2m, cls.ort]

        super().setUpTestData()

    @translation_override(language=None)
    def test_log_add_add(self):
        rel = _models.Ort.band_set.rel

        view = self.get_dummy_view(request=self.get_request())
        logs = view.log_add(self.ort, rel, self.obj2)
        self.assertEqual(logs[0].get_change_message(), 'Added Band "Testband".')
        self.assertEqual(logs[0].action_flag, ADDITION)
        self.assertEqual(logs[1].get_change_message(), 'Changed Orte.')
        self.assertEqual(logs[1].action_flag, CHANGE)

    @translation_override(language=None)
    def test_log_add_change(self):
        rel = _models.Ort.band_set.rel

        view = self.get_dummy_view(request=self.get_request())
        logs = view.log_add(self.ort, rel, self.obj2)
        self.assertEqual(logs[1].get_change_message(), 'Changed Orte.')
        self.assertEqual(logs[1].action_flag, CHANGE)

    @translation_override(language=None)
    def test_log_addition(self):
        view = self.get_dummy_view(request=self.get_request())
        log_entry = view.log_addition(self.obj1)
        self.assertEqual(log_entry.get_change_message(), 'Added.')
        self.assertEqual(log_entry.action_flag, ADDITION)

    @translation_override(language=None)
    def test_log_addition_m2m(self):
        view = self.get_dummy_view(request=self.get_request())
        log_entry = view.log_addition(self.obj1, self.m2m)
        expected = 'Added {name} "{object}".'.format(
            name=self.m2m._meta.verbose_name, object=force_text(self.m2m))
        self.assertEqual(log_entry.get_change_message(), expected)
        self.assertEqual(log_entry.action_flag, ADDITION)

    @translation_override(language=None)
    def test_log_change(self):
        view = self.get_dummy_view(request=self.get_request())
        log_entry = view.log_change(self.obj1, ['band_name'])
        self.assertEqual(log_entry.get_change_message(), 'Changed Bandname.')
        self.assertEqual(log_entry.action_flag, CHANGE)

    @translation_override(language=None)
    def test_log_change_fields_is_no_list(self):
        view = self.get_dummy_view(request=self.get_request())
        log_entry = view.log_change(self.obj1, 'band_name')
        self.assertEqual(log_entry.get_change_message(), 'Changed Bandname.')
        self.assertEqual(log_entry.action_flag, CHANGE)
        log_entry = view.log_change(self.obj1, {'band_name': 'Boop'})
        self.assertEqual(log_entry.get_change_message(), 'Changed Bandname.')
        self.assertEqual(log_entry.action_flag, CHANGE)

    @translation_override(language=None)
    def test_log_change_m2m(self):
        view = self.get_dummy_view(request=self.get_request())
        log_entry = view.log_change(self.obj1, ['genre'], self.m2m)
        expected = 'Changed {fields} for {name} "{object}".'.format(
            fields=capfirst(self.m2m._meta.get_field('genre').verbose_name),
            name=capfirst(self.m2m._meta.verbose_name),
            object=force_text(self.m2m)
        )
        self.assertEqual(log_entry.get_change_message(), expected)
        self.assertEqual(log_entry.action_flag, CHANGE)

    @translation_override(language=None)
    def test_log_delete(self):
        qs = self.model.objects.all()

        view = self.get_dummy_view(request=self.get_request())
        logs = view.log_delete(qs)
        for l in logs:
            self.assertEqual(l.get_change_message(), '')
            self.assertEqual(l.action_flag, DELETION)

    @translation_override(language=None)
    def test_log_deletion(self):
        view = self.get_dummy_view(request=self.get_request())
        log_entry = view.log_deletion(self.obj1)
        self.assertEqual(log_entry.get_change_message(), '')
        self.assertEqual(log_entry.action_flag, DELETION)

    @translation_override(language=None)
    def test_log_update(self):
        view = self.get_dummy_view(request=self.get_request())
        qs = self.model.objects.all()
        update_data = dict(beschreibung='No update.', orte=self.ort)
        logs = view.log_update(qs, update_data)
        expected = 'Changed Beschreibung and Orte.'
        for l in logs:
            self.assertEqual(l.get_change_message(), expected)
            self.assertEqual(l.action_flag, CHANGE)

    @translation_override(language=None)
    def test_get_logger(self):
        request = self.get_request()
        logger = get_logger(request)
        self.assertEqual(logger.request, request)
        log_entry = logger.log_change(self.obj1, ['band_name'])
        self.assertEqual(log_entry.get_change_message(), 'Changed Bandname.')
        self.assertEqual(log_entry.action_flag, CHANGE)

    def test_get_logger_addition_fails_silently(self):
        logger = get_logger(None)
        with self.assertNotRaises(AttributeError):
            log_entry = logger.log_addition(self.obj1)
        self.assertIsNone(log_entry)

    def test_get_logger_change_fails_silently(self):
        logger = get_logger(None)
        with self.assertNotRaises(AttributeError):
            log_entry = logger.log_change(self.obj1, ['band_name'])
        self.assertIsNone(log_entry)

    def test_get_logger_deletion_fails_silently(self):
        logger = get_logger(None)
        with self.assertNotRaises(AttributeError):
            log_entry = logger.log_deletion(self.obj1)
        self.assertIsNone(log_entry)

    def test_get_logger_fails_loudly(self):
        # Should raise errors if they're not AttributeError, f.ex. a TypeError
        # for missing arguments.
        logger = get_logger(None)
        with self.assertRaises(TypeError):
            logger.log_deletion()
