import requests_mock
from requests.exceptions import HTTPError

from dbentry.utils import gnd
from tests.case import MIZTestCase


@requests_mock.Mocker()
class TestGND(MIZTestCase):
    # Sample xml in RDFxml format:
    rdf_xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <searchRetrieveResponse xmlns="default" xmlns:rdf="rdf" xmlns:gndo="gndo">
            <version>1.1</version>
            <numberOfRecords>864</numberOfRecords>
            <records>
                <record>
                    <recordData>
                        <gndo:gndIdentifier>124182054</gndo:gndIdentifier>
                        <gndo:preferredNameForThePerson>Lindemann, Till</gndo:preferredNameForThePerson>
                    </recordData>
                </record>
                <record>
                    <recordData>
                        <gndo:gndIdentifier>42</gndo:gndIdentifier>
                        <gndo:preferredNameForThePerson>Lustig, Peter</gndo:preferredNameForThePerson>
                    </recordData>
                </record>
            </records>
        </searchRetrieveResponse>
        """

    # URL for the requests_mock.Mocker.
    # Calls to this URL will be intercepted.
    url = 'http://test.com'

    def setUp(self):
        self.rdf_xml = self.rdf_xml.replace('\n', '').strip()
        super().setUp()

    def test_raises_4xx(self, mocked_request):
        """Assert that responses with 4xx status codes raise an exception."""
        mocked_request.get(self.url, text=self.rdf_xml, status_code=404)
        with self.assertRaises(HTTPError):
            gnd.searchgnd(url=self.url, query='test')

    def test_raises_5xx(self, mocked_request):
        """Assert that responses with 5xx status codes raise an exception."""
        mocked_request.get(self.url, text=self.rdf_xml, status_code=503)
        with self.assertRaises(HTTPError):
            gnd.searchgnd(url=self.url, query='test')

    def test_ignores_records_without_identifier_element(self, mocked_request):
        """
        Assert that records, for which no identifier element could be found,
        are not added to the result list.
        """
        modified_rdf_xml = self.rdf_xml.replace(
            '<gndo:gndIdentifier>124182054</gndo:gndIdentifier>',
            ''
        )
        mocked_request.get(self.url, text=modified_rdf_xml)
        results, _count = gnd.searchgnd(url=self.url, query='test')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], '42')

    def test_ignores_records_without_identifier_value(self, mocked_request):
        """
        Assert that records with missing identifier values are not added to the
        result list.
        """
        modified_rdf_xml = self.rdf_xml.replace('124182054', '')
        mocked_request.get(self.url, text=modified_rdf_xml)
        results, _count = gnd.searchgnd(url=self.url, query='test')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], '42')

    def test_no_label_element(self, mocked_request):
        """
        Assert that the id value is used as a label if any elements that could
        provide a label are missing.
        """
        modified_rdf_xml = self.rdf_xml.replace(
            '<gndo:preferredNameForThePerson>Lindemann, Till</gndo:preferredNameForThePerson>',
            ''
        )
        mocked_request.get(self.url, text=modified_rdf_xml)
        results, _count = gnd.searchgnd(url=self.url, query='test')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][1], '124182054')

    def test_no_label_element_text(self, mocked_request):
        """
        Assert that the id value is used as a label if elements that could
        provide a label have no text value.
        """
        modified_rdf_xml = self.rdf_xml.replace('Lindemann, Till', '')
        mocked_request.get(self.url, text=modified_rdf_xml)
        results, _count = gnd.searchgnd(url=self.url, query='test')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][1], '124182054')

    def test_returns_total_number_of_matches(self, mocked_request):
        """
        Assert that searchgnd returns the total number of matches according
        to the value of xml element 'numberOfRecords'.
        """
        mocked_request.get(self.url, text=self.rdf_xml)
        results, count = gnd.searchgnd(url=self.url, query='Peter')
        self.assertEqual(count, 864)

    def test_no_query_string(self, mocked_request):
        """Assert that searchgnd short circuits when query string is missing."""
        mocked_request.get(self.url, text=self.rdf_xml)
        results, count = gnd.searchgnd(url=self.url, query='')
        self.assertFalse(results)
        self.assertEqual(count, 0)

    def test_number_of_records_element_missing(self, mocked_request):
        """
        Assert that searchgnd returns empty when a numberOfRecords element
        could not be found.
        """
        modified_rdf_xml = self.rdf_xml.replace('<numberOfRecords>864</numberOfRecords>', '')
        mocked_request.get(self.url, text=modified_rdf_xml)
        with self.assertNotRaises(AttributeError):
            results, count = gnd.searchgnd(url=self.url, query='test')
        self.assertFalse(results)
        self.assertEqual(count, 0)

    def test_number_of_records_element_none(self, mocked_request):
        """
        Assert that searchgnd returns empty when the numberOfRecords element
        has an inappropriate value for int().
        """
        modified_rdf_xml = self.rdf_xml.replace(
            '<numberOfRecords>864</numberOfRecords>',
            '<numberOfRecords>None</numberOfRecords>'
        )
        mocked_request.get(self.url, text=modified_rdf_xml)
        with self.assertNotRaises(ValueError):
            results, count = gnd.searchgnd(url=self.url, query='test')
        self.assertFalse(results)
        self.assertEqual(count, 0)
