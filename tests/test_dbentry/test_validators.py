from django.core.exceptions import ValidationError

from dbentry.validators import (
    DiscogsMasterReleaseValidator,
    DiscogsURLValidator,
    DNBURLValidator,
    EANValidator,
    InvalidChecksum,
    InvalidComponent,
    InvalidFormat,
    InvalidLength,
    ISBNValidator,
    ISSNValidator,
)
from tests.case import MIZTestCase


class TestISBNValidator(MIZTestCase):
    def test_valid(self):
        """Assert that validating valid values does not produce ValidationErrors."""
        validator = ISBNValidator
        valid = ["9781234567897", "978-1-234-56789-7"]
        for valid_value in valid:
            with self.subTest(value=valid_value):
                with self.assertNotRaises(ValidationError):
                    validator(valid_value)

    def test_invalid(self):
        """Assert that validating an invalid value raises a specific error."""
        validator = ISBNValidator
        invalid = [
            ("99 99!)()/?1*", InvalidFormat),
            ("9" * 20, InvalidLength),
            ("1234567890128", InvalidComponent),
            ("1234567890", InvalidChecksum),
            ("1-234-56789-0", InvalidChecksum),
            ("9781234567890", InvalidChecksum),
            ("978-1-234-56789-0", InvalidChecksum),
        ]
        for invalid_value, expected_exception in invalid:
            with self.subTest(value=invalid_value):
                with self.assertRaises(expected_exception):
                    validator(invalid_value)


class TestISSNValidator(MIZTestCase):
    def test_valid(self):
        """Assert that validating valid values does not produce ValidationErrors."""
        validator = ISSNValidator
        valid = ["12345679", "1234-5679"]
        for valid_value in valid:
            with self.subTest(value=valid_value):
                with self.assertNotRaises(ValidationError):
                    validator(valid_value)

    def test_invalid(self):
        """Assert that validating an invalid value raises a specific error."""
        validator = ISSNValidator
        invalid = [
            ("12 3%&/79", InvalidFormat),
            ("9" * 20, InvalidLength),
            ("12345670", InvalidChecksum),
            ("1234-5670", InvalidChecksum),
        ]
        for invalid_value, expected_exception in invalid:
            with self.subTest(value=invalid_value):
                with self.assertRaises(expected_exception):
                    validator(invalid_value)


class TestEANValidator(MIZTestCase):
    def test_valid(self):
        """Assert that validating valid values does not produce ValidationErrors."""
        validator = EANValidator
        valid = ["1234567890128", "123-4-567-89012-8"]
        for valid_value in valid:
            with self.subTest(value=valid_value):
                with self.assertNotRaises(ValidationError):
                    validator(valid_value)

    def test_invalid(self):
        """Assert that validating an invalid value raises a specific error."""
        validator = EANValidator
        invalid = [
            ("12 3%&/()90128", InvalidFormat),
            ("9" * 20, InvalidLength),
            ("73513538", InvalidChecksum),
            ("1234567890123", InvalidChecksum),
        ]
        for invalid_value, expected_exception in invalid:
            with self.subTest(value=invalid_value):
                with self.assertRaises(expected_exception):
                    validator(invalid_value)


class TestDiscogsURLValidator(MIZTestCase):
    def setUp(self):
        self.validator = DiscogsURLValidator()

    def test_valid(self):
        """Assert that discogs URLs pass as valid."""
        urls = [
            "https://www.discogs.com/release/4126",
            "www.discogs.com/release/4126",
            "discogs.com/release/4126",
            "https://www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin",
            "www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin",
            "discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin",
            # I believe discogs has since stopped using this URL format:
            "https://www.discogs.com/Manderley--Fliegt-Gedanken-Fliegt-/release/3512181",
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertNotRaises(ValidationError):
                    self.validator(url)

    def test_invalid(self):
        """Assert that URLs without discogs.com as host produce ValidationErrors."""
        invalid_urls = ["https://www.google.com", "www.google.com", "google.com", "invalid/discogs.com"]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError) as cm:
                    self.validator(url)
                self.assertEqual(cm.exception.message, "Bitte nur Adressen von discogs.com eingeben.")
                self.assertEqual(cm.exception.code, "discogs")


class TestDiscogsMasterReleaseValidator(MIZTestCase):
    def setUp(self):
        self.validator = DiscogsMasterReleaseValidator()

    def test_valid(self):
        """Assert that discogs URLs of 'releases' pass as valid."""
        urls = [
            "https://www.discogs.com/release/4126",
            "www.discogs.com/release/4126",
            "discogs.com/release/4126",
            "https://www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin",
            "www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin",
            "discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin",
            # I believe discogs has since stopped using this URL format:
            "https://www.discogs.com/Manderley--Fliegt-Gedanken-Fliegt-/release/3512181",
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertNotRaises(ValidationError):
                    self.validator(url)

    def test_master_url(self):
        """
        Assert that URLs for 'master releases' (a meta release of sorts) raise
        a ValidationError.
        """
        urls = [
            "https://www.discogs.com/master/4126",
            "www.discogs.com/master/4126",
            "discogs.com/master/4126",
            "https://www.discogs.com/master/4126-Led-Zeppelin-Led-Zeppelin",
            "www.discogs.com/master/4126-Led-Zeppelin-Led-Zeppelin",
            "discogs.com/master/4126-Led-Zeppelin-Led-Zeppelin",
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError) as cm:
                    self.validator(url)
                self.assertEqual(cm.exception.message, "Bitte keine Adressen von Master-Releases eingeben.")
                self.assertEqual(cm.exception.code, "master_release")


class TestDNBURLValidator(MIZTestCase):
    def setUp(self):
        self.validator = DNBURLValidator()

    def test_valid(self):
        """Assert that DNB URLs pass as valid."""
        urls = [
            "http://d-nb.info/gnd/11863996X",
            "https://d-nb.info/gnd/11863996X",
            "https://portal.dnb.de/opac.htm?method=simpleSearch&cqlMode=true&query=nid%3D11863996X",
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertNotRaises(ValidationError):
                    self.validator(url)

    def test_invalid(self):
        """Assert that invalid or non-DNB URLs raise a ValidationError."""
        urls = ["notavalidurl", "www.google.com"]
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError) as cm:
                    self.validator(url)
                self.assertEqual(
                    cm.exception.message, "Bitte nur Adressen der DNB eingeben (d-nb.info oder portal.dnb.de)."
                )
                self.assertEqual(cm.exception.code, "dnb")
