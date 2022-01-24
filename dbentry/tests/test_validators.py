from django.core.exceptions import ValidationError
from django.utils.translation import override as translation_override

from dbentry.tests.base import MyTestCase
from dbentry.validators import (
    DiscogsMasterReleaseValidator, ISSNValidator, ISBNValidator, EANValidator,
    InvalidChecksum, InvalidComponent, InvalidFormat, InvalidLength,
    DiscogsURLValidator, DNBURLValidator
)


class TestStdNumValidators(MyTestCase):
    # Assert that the validators re-raise the correct django.ValidationError subclass.

    @translation_override(language=None)
    def run_validators(self, validator, invalid):
        msg = "\nUnexpected exception raised. Expected: {}, got: {}"
        for invalid_number, exception_class in invalid:
            with self.subTest(invalid_number=invalid_number):
                with self.assertRaises(ValidationError) as cm:
                    validator(invalid_number)
                self.assertEqual(
                    cm.exception.__class__, exception_class,
                    msg=msg.format(cm.exception.__class__.__name__, exception_class.__name__)
                )

    def test_isbn_validator(self):
        invalid = [
            ("99 99!)()/?1*", InvalidFormat),
            ("9" * 20, InvalidLength),
            ("1234567890128", InvalidComponent),
            ('1234567890', InvalidChecksum),
            ('1-234-56789-0', InvalidChecksum),
            ('9781234567890', InvalidChecksum),
            ('978-1-234-56789-0', InvalidChecksum),
        ]
        self.run_validators(ISBNValidator, invalid)

    def test_issn_validator(self):
        invalid = [
            ("12 3%&/79", InvalidFormat),
            ("9" * 20, InvalidLength),
            ('12345670', InvalidChecksum),
            ("1234-5670", InvalidChecksum),
        ]
        self.run_validators(ISSNValidator, invalid)

    def test_ean_validator(self):
        invalid = [
            ("12 3%&/()90128", InvalidFormat),
            ("9" * 20, InvalidLength),
            ('73513538', InvalidChecksum),
            ("1234567890123", InvalidChecksum),
        ]
        self.run_validators(EANValidator, invalid)


class TestDiscogsURLValidator(MyTestCase):

    def setUp(self):
        self.validator = DiscogsURLValidator()

    def test_valid_urls(self):
        # Assert that these valid URLs pass.
        urls = [
            'https://www.discogs.com/release/4126',
            'www.discogs.com/release/4126',
            'discogs.com/release/4126',
            'https://www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            'www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            'discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            # I believe discogs has since stopped using this URL format:
            'https://www.discogs.com/Manderley--Fliegt-Gedanken-Fliegt-/release/3512181',
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertNotRaises(ValidationError):
                    self.validator(url)

    def test_invalid_urls(self):
        # Assert that URLs without discogs.com as host produce ValidationErrors.
        invalid_urls = [
            'https://www.google.com',
            'www.google.com',
            'google.com',
            'invalid/discogs.com'
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError) as cm:
                    self.validator(url)
                self.assertEqual(cm.exception.message, "Bitte nur Adressen von discogs.com eingeben.")
                self.assertEqual(cm.exception.code, 'discogs')


class TestDiscogsMasterReleaseValidator(MyTestCase):

    def setUp(self):
        self.validator = DiscogsMasterReleaseValidator()

    def test_release_url(self):
        # Assert that 'release' URLs pass.
        urls = [
            'https://www.discogs.com/release/4126',
            'www.discogs.com/release/4126',
            'discogs.com/release/4126',
            'https://www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            'www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            'discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            # I believe discogs has since stopped using this URL format:
            'https://www.discogs.com/Manderley--Fliegt-Gedanken-Fliegt-/release/3512181',
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertNotRaises(ValidationError):
                    self.validator(url)

    def test_master_url(self):
        # Assert that an URL for a 'master release' (a meta release of sorts)
        # is invalid.
        urls = [
            'https://www.discogs.com/master/4126',
            'www.discogs.com/master/4126',
            'discogs.com/master/4126',
            'https://www.discogs.com/master/4126-Led-Zeppelin-Led-Zeppelin',
            'www.discogs.com/master/4126-Led-Zeppelin-Led-Zeppelin',
            'discogs.com/master/4126-Led-Zeppelin-Led-Zeppelin',
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError) as cm:
                    self.validator(url)
                self.assertEqual(cm.exception.message, "Bitte keine Adressen von Master-Releases eingeben.")
                self.assertEqual(cm.exception.code, 'master_release')


class TestDNBURLValidator(MyTestCase):

    def setUp(self):
        self.validator = DNBURLValidator()

    def test_invalid_url(self):
        msg = "ValidationError not raised for invalid url."
        urls = ['notavalidurl', 'www.google.com']
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError, msg=msg) as cm:
                    self.validator(url)
                self.assertEqual(
                    cm.exception.message,
                    "Bitte nur Adressen der DNB eingeben (d-nb.info oder portal.dnb.de)."
                )
                self.assertEqual(cm.exception.code, 'dnb')

    def test_valid_url(self):
        msg = "ValidationError raised for valid url."
        urls = [
            'http://d-nb.info/gnd/11863996X',
            'https://d-nb.info/gnd/11863996X',
            'https://portal.dnb.de/opac.htm?method=simpleSearch&cqlMode=true&query=nid%3D11863996X',
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertNotRaises(ValidationError, msg=msg):
                    self.validator(url)
