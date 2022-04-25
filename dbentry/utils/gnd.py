import io
import logging
from typing import List, Tuple
from xml.etree import ElementTree

import requests  # type: ignore[import]

logger = logging.getLogger(__name__)


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
) -> Tuple[List[Tuple[str, str]], int]:
    """
    Query the GND of the DNB and return a list of matching (id, label) pairs.

    Using the Search/Retrieve via URL (SRU) API, query the authority file of the
    German national library and extract the GND id and a text representation of
    the records found. Parameter ``identifier`` is the name (tag) of the XML
    element that contains the id number.
    Parameter ``labels`` is a list of names of elements with text values
    suitable as a text representation of the record (i.e. names or titles).
    Per record, the value of the first such element will be used. If the record
    doesn't have any elements with names declared in ``labels``, the id value
    will be used as a label instead.

    Args:
        query (str): SRU format compliant query string
            See: https://www.dnb.de/DE/Professionell/Metadatendienste/Datenbezug/SRU/sru_node.html
        start (str): request parameter for pagination: result index of the first
            record of the page
        url (str): address of the API endpoint for the authority file
        version (str): SRU version number (request parameter)
        operation (str): server command (request parameter)
        schema (str): data format of the response text (request parameter)
        identifier (str): the tag of the xml element that holds the GND ID
        labels (Tuple[str]): tags of the elements whose texts could serve as
            labels for the selection
        **params (List[str]): additional request parameters

    Returns:
        A 2-tuple with one item being the result list and the other being the
            total number of matches found. The result list is a list of
            (id, text label) 2-tuples.

    Raises:
        requests.exceptions.HTTPError: if response status code is 4xx or 5xx.
    """
    if not query:
        return [], 0

    request_params = {
        'query': [query],
        'version': [version],
        'operation': [operation],
        'recordSchema': [schema],
        'startRecord': [start],
        **params
    }
    logger.info(f'Sending request to {url!r} using parameters {request_params!r}.')
    response = requests.get(url, request_params)
    logger.info(f'DNB SRU response status code: {response.status_code!r}')
    response.raise_for_status()  # raise 4xx and 5xx errors

    # Gather the namespaces and set the default namespace 'sru'.
    namespaces = dict(
        [
            node
            for _, node in ElementTree.iterparse(io.StringIO(response.text), events=['start-ns'])
        ]
    )
    namespaces['sru'] = namespaces['']

    root = ElementTree.fromstring(response.text)
    # Get the total number of matches:
    try:
        result_count = int(root.find('.//sru:numberOfRecords', namespaces).text)  # type: ignore[union-attr, arg-type]  # noqa
    except AttributeError as exc:
        logger.error(
            "Could not find element 'sru:numberOfRecords' or the element found "
            f"has no 'text' attribute. \nNamespaces used: {namespaces!r}"
            f"\nError message: {exc!s}"
        )
        return [], 0
    except ValueError as exc:
        logger.error(
            f"Inappropriate text value for the 'numberOfRecords' element. Error message: {exc!s}"
        )
        return [], 0

    # Get the records returned in this batch.
    # Note that by default SRU returns 10 records at a time.
    records = root.findall('.//sru:recordData', namespaces)
    logger.info(f'SRU response returned {len(records)} of {result_count} matching records.')

    results = []
    for record in records:
        identifier_element = record.find(f".//{identifier!s}", namespaces)
        if identifier_element is None:
            logger.warning(f"Record data contained no element with identifier tag {identifier!r}.")
            continue
        if not getattr(identifier_element, 'text', None):
            # Reject elements without an ID value:
            logger.warning(f"No ID value found on element {identifier_element!r}.")
            continue
        id_number: str = identifier_element.text  # type: ignore[assignment]
        # Use the text from the first element that has text as a label for this
        # particular match.
        label: str = id_number
        for label_tag in labels:
            label_element = record.find(f'.//{label_tag}', namespaces)
            if label_element is not None and label_element.text:
                label = label_element.text
                break
        results.append((id_number, label))
    return results, result_count
