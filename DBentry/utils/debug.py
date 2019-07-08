import time

def timethis(func, *args, **kwargs):
    ts = time.time()
    func(*args, **kwargs)
    te = time.time()
    return te - ts
    
def num_queries(func=None, *args, **kwargs):
    from django.test.utils import CaptureQueriesContext
    from django.db import connections, DEFAULT_DB_ALIAS
    using = kwargs.pop("using", DEFAULT_DB_ALIAS)
    conn = connections[using]

    context = CaptureQueriesContext(conn)
    if func is None:
        # return the context manager so the caller can use it 
        return context

    with context as n:
        func(*args, **kwargs)
    return len(n)
    
def debug_queryfunc(func, *args, **kwargs):
    with num_queries() as n:
        t = timethis(func, *args, **kwargs)
    n = len(n)
    print("Time:", t)
    print("Num. queries:", n)
    return t, n
