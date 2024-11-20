"""
Test model: tests.test_utils.models.Audio

Many-To-Many to Band: Band <-> Audio
Reverse FK to Bestand: Bestand -> Audio
"""

from unittest.mock import patch, Mock

from django.urls import NoReverseMatch

from dbentry.utils import changelist_links as utils
from tests.case import DataTestCase
from tests.model_factory import make
from tests.test_utils.models import Audio, Band, Bestand, Musiker


class TestChangelistLinks(DataTestCase):
    model = Audio
    model_relations = [Audio.band.rel, Audio.musiker.rel, Bestand._meta.get_field("audio").remote_field]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.band = band = make(Band, band_name="Foo Fighters")
        cls.audio1 = make(Audio, band=[band])
        cls.audio2 = make(Audio, band=[band])

    @patch("dbentry.utils.changelist_links.get_model_relations", new=Mock(return_value=model_relations))
    def test_get_changelist_link_relations(self):
        """
        Assert that get_changelist_link_relations returns the expected relation
        objects.
        """
        self.assertEqual(
            utils.get_changelist_link_relations(Audio, inline_models=[Audio.musiker.through]),
            [Audio.band.rel, Bestand._meta.get_field("audio").remote_field],
        )

    @patch("dbentry.utils.changelist_links.get_model_relations", new=Mock(return_value=model_relations))
    def test_get_changelist_link_relations_inline_models(self):
        """
        Assert that get_changelist_link_relations ignores relations to models that
        are included in the inline models.
        """
        self.assertNotIn(
            Audio.musiker.rel, utils.get_changelist_link_relations(Audio, inline_models=[Audio.musiker.through])
        )

    def test_get_rel_info(self):
        """Assert that get_rel_info returns the expected model and field."""
        self.assertEqual(utils.get_rel_info(Audio, Bestand._meta.get_field("audio").remote_field), (Bestand, "audio"))

    def test_get_rel_info_symmetric_m2m_relation(self):
        """Assert that get_rel_info ???"""
        self.assertEqual(utils.get_rel_info(Audio, Audio.musiker.rel), (Musiker, "audio"))
        self.assertEqual(utils.get_rel_info(Musiker, Audio.musiker.rel), (Audio, "musiker"))

    @patch("dbentry.utils.changelist_links.get_rel_info", new=Mock(return_value=(Audio, "band")))
    def test_get_relation_count(self):
        """Assert that get_relation_count returns the expected count."""
        self.assertEqual(utils.get_relation_count(Band, self.band.pk, Audio.band.rel), 2)

    @patch("dbentry.utils.changelist_links.get_rel_info", new=Mock(return_value=(Band, "audio")))
    @patch("dbentry.utils.changelist_links.reverse", new=Mock(return_value="/test/audio/"))
    def test_get_changelist_link_url(self):
        """Assert that get_changelist_link_url returns the expected URL."""

        def callback(*args):
            return "test_audio_changelist"

        self.assertEqual(
            utils.get_changelist_link_url(Band, self.band.pk, Audio.band.rel, callback),
            f"/test/audio/?audio={self.band.pk}",
        )

    @patch("dbentry.utils.changelist_links.get_rel_info", new=Mock(return_value=(Band, "audio")))
    @patch("dbentry.utils.changelist_links.reverse", new=Mock(side_effect=NoReverseMatch))
    def test_get_changelist_link_url_no_reverse_match(self):
        """
        Assert that get_changelist_link_url returns None if the changelist URL
        could not be reversed.
        """
        self.assertIsNone(utils.get_changelist_link_url(Band, self.band.pk, Audio.band.rel, lambda m: ""))

    @patch("dbentry.utils.changelist_links.get_rel_info", new=Mock(return_value=(Audio, "band")))
    def test_get_changelist_link_label_labels_override(self):
        self.assertEqual(utils.get_changelist_link_label(Band, Audio.band.rel, labels={"audio": "Foobar"}), "Foobar")

    @patch("dbentry.utils.changelist_links.get_rel_info", new=Mock(return_value=(Audio, "band")))
    def test_get_changelist_link_label_related_name(self):
        with patch.object(Audio.band.rel, "related_name", new="foo_bar"):
            self.assertEqual(utils.get_changelist_link_label(Band, Audio.band.rel), "Foo Bar")

    @patch("dbentry.utils.changelist_links.get_rel_info", new=Mock(return_value=(Audio, "band")))
    def test_get_changelist_link_label_verbose_plural_name(self):
        self.assertEqual(utils.get_changelist_link_label(Band, Audio.band.rel), "Audio-Materialien")
