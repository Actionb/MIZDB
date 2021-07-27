import io
import logging
import requests

from typing import List, Tuple
from xml.etree import ElementTree

logger = logging.getLogger(__name__)


# TODO: pagination/scrolling (nextRecordPosition)
def searchgnd(
        query: str,
        start: str = '1',
        url: str = 'https://services.dnb.de/sru/authorities?',
        version: str = '1.1',
        operation: str = 'searchRetrieve',
        schema: str = 'RDFxml',
        identifier: str = 'gndo:gndIdentifier',
        labels: Tuple[str] = ('gndo:preferredNameForThePerson',),
        **params: List[str]
) -> List[Tuple[str, str]]:
    """
    Query the GND of the DNB and return a list of matching (id, label) pairs.

    Using the SRU (Search/Retrieve via URL) API, query the authority file of the
    German national library and extract the GND id and a text representation of
    the records found. Parameter `identifier` is the name (tag) of the XML
    element that contains the id number.
    Parameter `labels` is a list of names of elements with text values suitable
    as a text representation of the record (i.e. names or titles).
    Per record, the value of the first such element will be used. If the record
    doesn't have any elements with names declared in `labels`, the id value be
    used as a label instead.

    Args:
        query (str): SRU format compliant query string.
            See: https://www.dnb.de/DE/Professionell/Metadatendienste/Datenbezug/SRU/sru_node.html
        start (str): request parameter for pagination: result index of the first
            record of the page.
        url (str): address of the API endpoint for the authority file.
        version (str): SRU version number (request parameter).
        operation (str): server command (request parameter).
        schema (str): data format of the response text (request parameter).
        identifier (str): the tag of the xml element that holds the GND ID.
        labels (Tuple[str]): tags of the elements whose texts could serve as
            labels for the selection.
        **params (List[str]): additional request parameters.

    Returns:
        A list of (id, text label) 2-tuples: List[Tuple[str, str]].

    Raises:
        requests.exceptions.HTTPError: if response status code is 4xx or 5xx.
    """
    request_params = {
        'query': [query],
        'version': [version],
        'operation': [operation],
        'recordSchema': [schema],
        'startRecord': [start],
        **params
    }
    logger.info('Sending request to %r using parameters %r.', url, request_params)
    response = requests.get(url, request_params)
    logger.info('DNB SRU response status code: %s', response.status_code)
    response.raise_for_status()  # raise 4xx and 5xx errors

    # Gather the namespaces and set the default namespace 'sru'.
    namespaces = dict([
        node
        for _, node in ElementTree.iterparse(io.StringIO(response.text), events=['start-ns'])
    ])
    namespaces['sru'] = namespaces['']

    root = ElementTree.fromstring(response.text)
    records = root.findall('.//sru:recordData', namespaces)
    # Note that, by default, SRU only returns 10 records at a time.
    logger.info('SRU response returned %r matching records.', len(records))
    results = []
    for record in records:
        identifier_element = record.find(".//%s" % identifier, namespaces)
        if identifier_element is None:
            logger.warning("Record data contained no element with identifier tag %r.", identifier)
            continue
        if not getattr(identifier_element, 'text', None):
            logger.warning("No ID value found on element with identifier tag %r.", identifier)
            continue
        id_number = identifier_element.text
        # Use the text from the first element that has text as a label for this
        # particular match.
        label = id_number
        for label_tag in labels:
            label_element = record.find('.//%s' % label_tag, namespaces)
            if label_element is not None and label_element.text:
                label = label_element.text
                break
        results.append((id_number, label))
    return results
