from collections import OrderedDict


class InProcessCache(OrderedDict):

    def __init__(self, *args, **kwargs):
        self.limit = kwargs.pop('limit', 40)
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.limit:
            self.popitem(last=False)
