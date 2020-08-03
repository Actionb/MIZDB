from django.forms import Media

from DBentry import utils
from DBentry.tests.base import MyTestCase


class TestEnsureJQuery(MyTestCase):

    def setUp(self):
        super().setUp()
        from django.conf import settings
        self.jquery_base = 'admin/js/vendor/jquery/jquery%s.js' % (
            '' if settings.DEBUG else '.min'
        )
        self.jquery_init = 'admin/js/jquery.init.js'
        self.test_js = [
            ['beep', 'boop'],
            ['beep', self.jquery_base, 'boop', self.jquery_init],
            [self.jquery_init, self.jquery_base, 'beep', 'boop'],
            ['beep', 'boop', self.jquery_init]
        ]
        self.expected = [self.jquery_base, self.jquery_init, 'beep', 'boop']

    def test_ensure_jquery_media_object(self):
        # Assert that ensure_jquery adds jquery when given a Media object.
        media = Media(js=[])
        self.assertIsInstance(utils.ensure_jquery(media), Media)
        self.assertEqual(
            utils.ensure_jquery(media)._js,
            [self.jquery_base, self.jquery_init],
            msg="ensure_jquery should add jquery to empty media"
        )

        for js in self.test_js:
            media = Media(js=js)
            with self.subTest():
                self.assertEqual(utils.ensure_jquery(media)._js, self.expected)

    def test_ensure_jquery_as_func_decorator(self):
        # Assert that ensure_jquery adds jquery when decorating the
        # media function.
        def fake_media_func(media):
            return lambda *args: media
        func = fake_media_func(Media(js=[]))
        self.assertEqual(
            utils.ensure_jquery(func)(None)._js,
            [self.jquery_base, self.jquery_init]
        )

        for js in self.test_js:
            func = fake_media_func(Media(js=js))
            with self.subTest():
                self.assertEqual(
                    utils.ensure_jquery(func)(None)._js,
                    self.expected
                )

    def test_ensure_jquery_as_property_decorator(self):
        # Assert that ensure_jquery adds jquery when decorating the property
        # of the media function.
        def fake_property(_media):
            return property(lambda *args: _media)

        prop = fake_property(Media(js=[]))
        self.assertEqual(
            utils.ensure_jquery(prop).fget(1)._js,
            [self.jquery_base, self.jquery_init]
        )

        for js in self.test_js:
            prop = fake_property(Media(js=js))
            with self.subTest():
                self.assertEqual(
                    utils.ensure_jquery(prop).fget(1)._js,
                    self.expected
                )
