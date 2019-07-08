from nameparser import HumanName

from DBentry.constants import M2M_LIST_MAX_LEN

def concat_limit(values, width = M2M_LIST_MAX_LEN, sep = ", ", z = 0):
    """
    Joins string values of iterable 'values' up to a length of 'width', truncating the remainder.
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

def coerce_human_name(full_name):
    if not isinstance(full_name, (str, HumanName)):
        full_name = str(full_name)
    if isinstance(full_name, str):
        full_name = full_name.strip()
        if len(full_name.split()) == 1:
            # 'full_name' only contains a last name, 'trick' nameparser to treat it as such
            full_name = full_name + ","
        hn = HumanName(full_name)
    else:
        hn = full_name
    return hn

def parse_name(full_name):
    hn = coerce_human_name(full_name)
    return " ".join([hn.first, hn.middle]).strip(), hn.last
