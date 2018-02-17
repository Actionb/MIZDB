import time

from ..base import *

def timeit_wrapper(func, *args, **kwargs):
    def wrapped():
        return func(*args, **kwargs)
    return wrapped
    
@tag('timed')
class TimedTestCase(TestCase):
    
    file_name = ''
    file_path = 'DBentry/tests/timed/'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.file_name:
            self.file_name = "timed_test_results_{}.txt".format(self.__class__.__name)
        self.full_path = self.file_path + self.file_name
        # Truncate the log output
        file = open(self.full_path, 'w')
        file.close()
        
    def log_results(self, func_name, result):
        with open(self.full_path, 'a') as f:
            print("Timed function {}".format(func_name), file=f)
            print("Result is: {}".format(result), file=f)
            print("="*30, end="\n\n", file=f)
            
    def time(self, func, *args, **kwargs):
        func_name = kwargs.pop('func_name', None) or func.__name__
        ts = time.time()
        func(*args, **kwargs)
        te = time.time()
        result = te - ts
        #result = timeit.timeit(timeit_wrapper(func, *args, **kwargs))
        self.log_results(func_name, result)
