from .base import *

from django import views

from django.utils.text import get_text_list

from DBentry.logging import *

class TestLoggingMixin(ViewTestCase): 
    
    model = band
    view_class = type('DummyView', (LoggingMixin, views.View), {})
    
    @classmethod
    def setUpTestData(cls):        
        cls.obj1 = cls.model.objects.create(band_name='Logging')
        cls.obj2 = cls.model.objects.create(band_name='Testband', beschreibung='This is a test.')
        
        cls.genre = genre.objects.create(genre='Related')
        cls.m2m = band.genre.through.objects.create(band=cls.obj1, genre=cls.genre)
        cls.ort = ort.objects.create(land=land.objects.create(land_name='Merryland'))
        
        cls.test_data = [cls.obj1]
        
        super().setUpTestData()
        
    def test_log_add_add(self):
        rel = ort.band_set.rel
        
        view = self.view(self.get_request())
        logs = view.log_add(self.ort, rel, self.obj2)
        self.assertEqual(logs[0].get_change_message(), 'Band „Testband“ hinzugefügt.')
        self.assertEqual(logs[0].action_flag, ADDITION)
        self.assertEqual(logs[1].get_change_message(), 'Orte geändert.')
        self.assertEqual(logs[1].action_flag, CHANGE)
        
    def test_log_add_change(self):
        rel = ort.band_set.rel
        
        view = self.view(self.get_request())
        logs = view.log_add(self.ort, rel, self.obj2)
        self.assertEqual(logs[1].get_change_message(), 'Orte geändert.')
        self.assertEqual(logs[1].action_flag, CHANGE)
        
    def test_log_addition(self):
        view = self.view(self.get_request())
        l = view.log_addition(self.obj1)
        self.assertEqual(l.get_change_message(), gettext('Added.'))
        self.assertEqual(l.action_flag, ADDITION)
        
    def test_log_addition_m2m(self):
        view = self.view(self.get_request())
        l = view.log_addition(self.obj1, self.m2m)
        expected = gettext('Added {name} "{object}".').format(name=self.m2m._meta.verbose_name, object = force_text(self.m2m))
        self.assertEqual(l.get_change_message(), expected)
        self.assertEqual(l.action_flag, ADDITION)
        
    def test_log_change(self):
        view = self.view(self.get_request())
        l = view.log_change(self.obj1, ['band_name'])
        self.assertEqual(l.get_change_message(), 'Band_name geändert.')
        self.assertEqual(l.action_flag, CHANGE)
        
    def test_log_change_fields_is_no_list(self):
        view = self.view(self.get_request())
        l = view.log_change(self.obj1,'band_name')
        self.assertEqual(l.get_change_message(), 'Band_name geändert.')
        self.assertEqual(l.action_flag, CHANGE)
        l = view.log_change(self.obj1,{'band_name':'Boop'})
        self.assertEqual(l.get_change_message(), 'Band_name geändert.')
        self.assertEqual(l.action_flag, CHANGE)
        
    def test_log_change_m2m(self):
        view = self.view(self.get_request())
        l = view.log_change(self.obj1, ['genre'], self.m2m)
        expected = gettext(
            'Changed {fields} for {name} "{object}".').format(
                fields='Genre', name=self.m2m._meta.verbose_name, object = force_text(self.m2m))
        self.assertEqual(l.get_change_message(), expected)
        self.assertEqual(l.action_flag, CHANGE)
    
    def test_log_delete(self):
        qs = self.model.objects.all()
        
        view = self.view(self.get_request())
        logs = view.log_delete(qs)
        for l in logs:
            self.assertEqual(l.get_change_message(), '')
            self.assertEqual(l.action_flag, DELETION)
        
    def test_log_deletion(self):
        view = self.view(self.get_request())
        l = view.log_deletion(self.obj1)
        self.assertEqual(l.get_change_message(), '')
        self.assertEqual(l.action_flag, DELETION)
        
    def test_log_update(self):
        view = self.view(self.get_request())
        qs = self.model.objects.all()
        update_data = dict(beschreibung='No update.', ort=self.ort)
        logs = view.log_update(qs, update_data)
        expected = 'Beschreibung und ort geändert.' 
        for l in logs:
            self.assertEqual(l.get_change_message(), expected)
            self.assertEqual(l.action_flag, CHANGE)
            
    def test_get_logger(self):
        request = self.get_request()
        logger = get_logger(request)
        self.assertEqual(logger.request, request)
        l = logger.log_change(self.obj1, ['band_name'])
        self.assertEqual(l.get_change_message(), 'Band_name geändert.')
        self.assertEqual(l.action_flag, CHANGE)
        
    def test_get_logger_addition_fails_silently(self):
        logger = get_logger(None)
        with self.assertNotRaises(AttributeError):
            l = logger.log_addition(self.obj1)
        self.assertIsNone(l)
        
    def test_get_logger_change_fails_silently(self):
        logger = get_logger(None)
        with self.assertNotRaises(AttributeError):
            l = logger.log_change(self.obj1, ['band_name'])
        self.assertIsNone(l)
        
    def test_get_logger_deletion_fails_silently(self):
        logger = get_logger(None)
        with self.assertNotRaises(AttributeError):
            l = logger.log_deletion(self.obj1)
        self.assertIsNone(l)
        
    def test_get_logger_fails_loudly(self):
        # Should raise errors if they're not AttributeError, f.ex. a TypeError for missing arguments
        logger = get_logger(None)
        with self.assertRaises(TypeError):
            l = logger.log_deletion()
        

