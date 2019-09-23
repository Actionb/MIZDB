from nameparser import HumanName

from DBentry.constants import M2M_LIST_MAX_LEN


def concat_limit(values, width=M2M_LIST_MAX_LEN, sep=", ", z=0):
    """
    Join string values of iterable 'values' separated by 'sep' up to a length
    of 'width', truncating the remainder. Items in 'values' that represent
    numericals will be 'z-filled' with 'z' number of zeros.
    """
    if not values:
        return ''
    rslt = str(values[0]).zfill(z)
    for v in values[1:]:
        if len(rslt) + len(str(v))<width:
            rslt += sep + str(v).zfill(z)
        else:
            rslt += sep + "[...]"
            break
    return rslt


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
