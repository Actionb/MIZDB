
def split_field(field_name, data, separators = [',']):
    """ Splits the content of data[field_name] according to separators and merges the new values back into a list of dicts."""
    if not data.get(field_name):
        return [data]
    rslt = []
    data_rest = {k:v for k, v in data.items() if k != field_name}
    for d in set(recmultisplit(data.get(field_name, ''), separators)):
        x = data_rest.copy()
        x.update({field_name:d})
        rslt.append(x)
    return rslt
    
def recmultisplit(values, separators = []):
    """Splits a string at each occurence of s in separators."""
    if len(separators)==1:
        return [i.strip() for i in values.split(separators[0])]
    rslt = []
    seps = separators[:]
    sep = seps.pop()
    
    for x in values.split(sep):
        rslt += recmultisplit(x, seps)
    return rslt   
