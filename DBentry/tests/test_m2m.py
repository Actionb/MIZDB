import DBentry.m2m as _m2m

from DBentry.tests.base import DataTestCase


class TestM2mAudioMusiker(DataTestCase):

    model = _m2m.m2m_audio_musiker
    raw_data = [{'musiker__kuenstler_name': 'Beep'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep')


class TestM2mVideoMusiker(DataTestCase):

    model = _m2m.m2m_video_musiker
    raw_data = [{'musiker__kuenstler_name': 'Beep Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')


class TestM2mDateiMusiker(DataTestCase):

    model = _m2m.m2m_datei_musiker
    raw_data = [{'musiker__kuenstler_name': 'Beep Boop'}]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Beep Boop')
