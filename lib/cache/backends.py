import pickle
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.locmem import LocMemCache as _LocMemCache

try:
    from django.utils.synch import RWLock
except ImportError:
    class RWLock: pass


class LocMemCache(_LocMemCache):
    def __init__(self, name, params):
        options = params.get('OPTIONS', {})
        max_size = options.get('MAX_SIZE', 1000000)
        try:
            self._max_size = int(max_size)
        except (ValueError, TypeError):
            self._max_size = 1000000
        super().__init__(name, params)
        if not hasattr(self, 'pickle_protocol'):
            self.pickle_protocol = pickle.HIGHEST_PROTOCOL

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        pickled = pickle.dumps(value, self.pickle_protocol)
        lock = self._lock
        if isinstance(lock, RWLock):
            lock = lock.writer()
        with lock:
            if self._has_expired(key):
                return self._set(key, pickled, timeout)
            return False

    def _set(self, key, value, *args, **kwargs):
        if len(value) > self._max_size:
            return False
        super()._set(key, value, *args, **kwargs)
        return True
