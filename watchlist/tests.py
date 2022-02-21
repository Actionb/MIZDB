import json
from importlib import import_module

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from dbentry.models import Genre
from dbentry.tests.base import UserTestCase
from dbentry.tests.mixins import TestDataMixin

from watchlist.models import Watchlist
from watchlist.views import get_watchlist, watchlist_toggle

User = get_user_model()


def add_session(request):
    engine = import_module(settings.SESSION_ENGINE)
    session = engine.SessionStore()
    session.save()
    request.session = session


class TestWatchlist(TestDataMixin, UserTestCase):

    model = Genre
    model_label = 'dbentry.genre'

    def setUp(self):
        self.rf = RequestFactory()
        self.watchlist = Watchlist.objects.filter(user=self.user)

    @classmethod
    def setUpTestData(cls):
        cls.content_type = ContentType.objects.get_for_model(cls.model)
        cls.user = User.objects.create_user(username='staff', password='Stuff', is_staff=True)
        cls.control = cls.model.objects.create(genre="Things")
        cls.new = cls.model.objects.create(genre="New")
        # Add the 'existing' object to the watchlist; it should remain on the
        # watchlist throughout each test.
        watch = Watchlist.objects.create(
            user=cls.user, content_type=cls.content_type,
            object_id=cls.control.pk, object_repr=str(cls.control)
        )
        cls.control_added = watch.added

    def test_watchlist_story(self):
        # Test the behaviour (UX) of the watchlist toggle.
        # TODO: this requires selenium
        ...

    def test_watchlist_toggle_add_model(self):
        """
        For authenticated users, watchlist_toggle should add items to the
        Watchlist model.
        """
        self.assertNotIn(self.new, self.watchlist)
        request = self.rf.get('/', data={'id': self.new.pk, 'model_label': self.model_label})
        request.user = self.user

        response = watchlist_toggle(request)
        self.assertIn(self.new.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertIn(self.control.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertTrue(json.loads(response.content)['on_watchlist'])

    def test_watchlist_toggle_add_session(self):
        """
        For unauthenticated users, watchlist_toggle should add items to the
        session store.
        """
        request = self.rf.get('/', data={'id': self.new.pk, 'model_label': self.model_label})
        request.user = AnonymousUser()
        add_session(request)
        request.session['watchlist'] = {self.model_label: [(self.control.pk, 'now')]}

        response = watchlist_toggle(request)
        pks = [pk for pk, time_added in request.session['watchlist'][self.model_label]]
        self.assertIn(self.new.pk, pks)
        self.assertIn(self.control.pk, pks)
        self.assertTrue(json.loads(response.content)['on_watchlist'])

    def test_watchlist_toggle_remove_model(self):
        """
        When watchlist_toggle receives a request for an item that is already on
        the watchlist, it should instead remove that item from the watchlist.

        Here: authenticated user -> remove from Watchlist *model*
        """
        Watchlist.objects.create(
            user=self.user, content_type=self.content_type,
            object_id=self.new.pk, object_repr=str(self.new)
        )
        request = self.rf.get('/', data={'id': self.new.pk, 'model_label': self.model_label})
        request.user = self.user

        response = watchlist_toggle(request)
        self.assertNotIn(self.new.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertIn(self.control.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertFalse(json.loads(response.content)['on_watchlist'])

    def test_watchlist_toggle_remove_session(self):
        """
        When watchlist_toggle receives a request for an item that is already on
        the watchlist, it should instead remove that item from the watchlist.

        Here: *UN*authenticated user -> remove from *session* watchlist
        """
        request = self.rf.get('/', data={'id': self.new.pk, 'model_label': self.model_label})
        request.user = AnonymousUser()
        add_session(request)
        request.session['watchlist'] = {
            self.model_label: [(self.control.pk, 'now'), (self.new.pk, 'later')]
        }

        response = watchlist_toggle(request)
        pks = [pk for pk, time_added in request.session['watchlist'][self.model_label]]
        self.assertNotIn(self.new.pk, pks)
        self.assertIn(self.control.pk, pks)
        self.assertFalse(json.loads(response.content)['on_watchlist'])

    def test_watchlist_toggle_remove_only_model(self):
        """
        watchlist_toggle must not add an item to the watchlist if the request
        is remove_only.
        """
        request = self.rf.get(
            '/', data={'id': self.new.pk, 'model_label': self.model_label, 'remove_only': True})
        request.user = self.user

        response = watchlist_toggle(request)
        self.assertNotIn(self.new.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertIn(self.control.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertFalse(json.loads(response.content)['on_watchlist'])

    def test_watchlist_toggle_remove_only_session(self):
        """
        watchlist_toggle must not add an item to the watchlist if the request
        is remove_only.
        """
        request = self.rf.get(
            '/', data={'id': self.new.pk, 'model_label': self.model_label, 'remove_only': True})
        request.user = AnonymousUser()
        add_session(request)
        request.session['watchlist'] = {self.model_label: [(self.control.pk, 'now')]}

        response = watchlist_toggle(request)
        pks = [pk for pk, time_added in request.session['watchlist'][self.model_label]]
        self.assertNotIn(self.new.pk, pks)
        self.assertIn(self.control.pk, pks)
        self.assertFalse(json.loads(response.content)['on_watchlist'])

    def test_watchlist_toggle_invalid_model(self):
        """watchlist_toggle should not try to add items of invalid models."""
        request = self.rf.get('/', data={'id': self.new.pk, 'model_label': 'hovercraft.eels'})
        request.user = self.user

        response = watchlist_toggle(request)
        self.assertNotIn(self.new.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertIn(self.control.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertFalse(json.loads(response.content)['on_watchlist'])

    def test_watchlist_toggle_invalid_instances(self):
        """watchlist_toggle should not try to add invalid model instances."""
        request = self.rf.get('/', data={'id': '-1', 'model_label': self.model_label})
        request.user = self.user

        response = watchlist_toggle(request)
        self.assertNotIn('-1', self.watchlist.values_list('object_id', flat=True))
        self.assertIn(self.control.pk, self.watchlist.values_list('object_id', flat=True))
        self.assertFalse(json.loads(response.content)['on_watchlist'])

    def test_get_watchlist(self):
        """
        For authenticated users, get_watchlist should return the watchlist
        from the Watchlist model.
        """
        request = self.rf.get('/')
        request.user = self.user
        self.assertEqual(
            {self.model_label: [(self.control.pk, self.control_added)]},
            get_watchlist(request)
        )

    def test_get_watchlist_session(self):
        """
        For unauthenticated users, get_watchlist should return the session
        watchlist.
        """
        request = self.rf.get('/')
        request.user = AnonymousUser()
        add_session(request)
        request.session['watchlist'] = 'session-watchlist'

        self.assertEqual(get_watchlist(request), 'session-watchlist')


# class TestWatchlist(ViewTestCase):
#
#     view_class = Watchlist
#
#     def test_watchlist_pk_has_become_invalid(self):
#         # Assert that the view can handle the situation in which an object
#         # saved to the watchlist has been deleted in the meantime.
#         ...


