from typing import Iterable, Tuple, Union

from nameparser import HumanName


def concat_limit(values: Iterable, width: int = 50, sep: str = ", ") -> str:
    """
    Join non-empty string values of iterable ``values`` separated by ``sep`` up
    to a length of ``width``, truncating the remainder.

    Passing width=0 disables the truncation.
    """
    results = ''
    for v in values:
        if not v:
            continue
        item = str(v)
        if not results:
            results = item
            continue
        if not width or len(results) + len(item) < width:
            results += sep + item
        else:
            results += sep + "[...]"
            break
    return results


def snake_case_to_spaces(value: str) -> str:
    return value.replace('_', ' ').strip()


def parse_name(full_name: Union[str, HumanName]) -> Tuple[str, str]:
    """
    Return a two-tuple of first names (including middle names) and last name.
    """
    if isinstance(full_name, str):
        full_name = full_name.strip()
        if len(full_name.split()) == 1:
            # The name consists of only the last name:
            return '', full_name
        hn = HumanName(full_name)
    else:
        hn = full_name
    return " ".join([hn.first, hn.middle]).strip(), hn.last
