
# DEBUG Printing

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
        
