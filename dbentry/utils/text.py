from nameparser import HumanName

from dbentry.constants import M2M_LIST_MAX_LEN


def concat_limit(values, width=M2M_LIST_MAX_LEN, sep=", ", z=0):
    """
    Join non-empty string values of iterable 'values' separated by 'sep' up to a
    length of current string + 'width', truncating the remainder.
    Passing width=0 disables the truncation.
    """
    # FIXME: z-fill was dropped in ca7fdee952ed1965ed320a42ef7892db3affdde8
    # and I don't really know why. Without z-fill, sorting Ausgabe instances by
    # their '_name' (i.e. alphabetically) will be poor:
    # '2000-11' comes before '2000-2' (should be: '2000-02')
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


def snake_case_to_spaces(value):
    return value.replace('_', ' ').strip()


def parse_name(full_name):
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
