
# DEBUG Printing

    
def print_tabular(to_print, columns = [], default_col_width=6):
    from itertools import chain
    if isinstance(to_print, dict):
        to_print = [to_print]
    if any(not isinstance(row, dict) for row in to_print):
        print ("Printing requires an iterable of dicts.")
        return
    
    column_ordering = columns[:] or list(set(chain(*[row.keys() for row in to_print])))
    # Allow column_ordering to consist of tuple/list with alias and key/name: (column_name,column_alias)
    for i, column in enumerate(column_ordering):
        if isinstance(column, tuple) and column[1]:
            continue
        else:
            column_ordering[i] = (column,column)
    
    # delete keys not existing in to_print.keys
    for key, alias in column_ordering:
        if any(key not in row.keys() for row in to_print):
            column_ordering.remove((key, alias))
    max_item_len = {}
    for row in to_print:
        for key, alias in column_ordering:
            try:
                len_v = len(str(row[key]))
            except:
                len_v = default_col_width
            max_item_len[key] = max(len_v, len(alias))+2
            
    header_string = ""
    for key, alias in column_ordering:
        header_string += "|" + alias.center(max_item_len[key]) + "|"
    print(header_string)
    print("="*len(header_string))
    for row in to_print:
        for key, alias in column_ordering:
            try:
                print("|"+str(row[key]).center(max_item_len[key])+"|", end="")
            except:
                print("column_ordering:", column_ordering)
                print("row.keys", row.keys())
        print()
    print()


def print_request(request, file=None):
    file = file or open('print_request.txt', 'w')
    def printf(txt):
        print(txt, file=file)
    for i in dir(request):
        if i == "__dict__":
            continue
        printf("~"*20)
        printf(i)
        printf(getattr(request, i, None))
        printf("")
    printf("\n\n DICT:")
    for k, v in request.__dict__.items():
        printf("~"*20)
        printf(k)
        printf(v)
        printf("")
        
