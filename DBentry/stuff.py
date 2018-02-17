seps = [',', '/', '+']

def multisplit(values, seperators = []):
    """Splits a string at each occurence of s in seperators."""
#    if len(seperators)==1:
#        return values.split(seperators[0])
    rslt = []
    last_sep = 0
    for index, c in enumerate(values):
        if c in seperators:
            rslt.append(values[last_sep:index].strip())
            last_sep = index+1
    rslt.append(values[last_sep:].strip())
    return rslt
    
def split_field(field_name, data, seperators = seps):
    split_data = list(set(multisplit(data.get(field_name, ''), seperators)))
    rslt = []
    data_rest = {k:v for k, v in data.items() if k != field_name}
    for d in split_data:
        x = data_rest.copy()
        x.update({field_name:d})
        rslt.append(x)
    return rslt
    
class X(object):
    
    a, b, c = (0, 0, 0)
    
if __name__ == '__main__':
    n = 'John Coltrane - Wilbur Harden'
    print(multisplit(n, [',', '-']))
    print()
