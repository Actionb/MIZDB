import re

class BaseHandler(object):

    regex = ''

    def __init__(self, regex=None):
        if regex is not None:
            self.regex = regex
        if isinstance(self.regex, str):
            self.regex = re.compile(self.regex)

    def __call__(self, item):
        return self.handle(item)

    def handle(self, item):
        raise NotImplementedError("Subclasses must implement this method.")

    def is_valid(self, item):
        return self.regex.search(item)

class NumericHandler(BaseHandler):

    regex = r'^\d+$'

    def handle(self, item):
        if self.is_valid(item):
            yield item

class RangeHandler(BaseHandler):

    regex = r'^(\d+)-(\d+)$'

    def handle(self, item):
        match = self.is_valid(item)
        if match:
            start, end = map(int, match.groups())
            for i in range(start, end+1):
                yield str(i)

class RangeGroupingHandler(BaseHandler):

    regex = r'^(\d+)-(\d+)\*(\d+)$'

    def handle(self, item):
        match = self.is_valid(item)
        if match:
            start, end, multi = map(int, match.groups())
            for i in range(start, end+1, multi):
                yield [str(i+j) for j in range(multi)]

class GroupingHandler(BaseHandler):

    regex = r'^\d+(/\d+)+$'

    def handle(self, item):
        if self.is_valid(item):
            yield item.split('/')
