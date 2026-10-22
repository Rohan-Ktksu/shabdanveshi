"""Small process-local caches; no query data is written to disk."""
from collections import OrderedDict
from time import monotonic


class ExpiringCache:
    def __init__(self, capacity, ttl=600, clock=monotonic):
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self.items = OrderedDict()

    def get(self, key):
        now = self.clock()
        for expired in [k for k, (deadline, _) in self.items.items() if deadline <= now]:
            del self.items[expired]
        if key not in self.items:
            return False, None
        _, value = self.items[key]
        self.items.move_to_end(key)
        return True, value

    def put(self, key, value):
        self.items[key] = (self.clock() + self.ttl, value)
        self.items.move_to_end(key)
        while len(self.items) > self.capacity:
            self.items.popitem(last=False)

    def clear(self):
        self.items.clear()
