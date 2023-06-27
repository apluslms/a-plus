from django.test import SimpleTestCase
from threading import Thread, Event, Barrier
from unittest.mock import patch

from lib.cache.cached_old import CachedAbstract


class TestCached(CachedAbstract):
    def __init__(self, func):
        self._fake_func = func
        super().__init__()

    def _generate_data(self, *models, data=None):
        return self._fake_func(data)


mock_cache = {}

def mock_delete(key):
    mock_cache.pop(key, None)

def mock_set(key, value, timeout=None): # pylint: disable=unused-argument
    mock_cache[key] = value

def mock_get(key, default=None):
    return mock_cache.get(key, default)

def mock_add(key, value, timeout=None): # pylint: disable=unused-argument
    if key not in mock_cache:
        mock_cache[key] = value
        return True
    return False


def cache_patcher():
    return patch.multiple('lib.cache.cached.cache',
        add=mock_add, delete=mock_delete,
        get=mock_get, set=mock_set)


@cache_patcher()
class CachedTest(SimpleTestCase):
    def setUp(self):
        mock_cache.clear()

    def test_gen_value(self):
        """
        Cache should return the generated value
        """
        data = "Some data"
        cached = TestCached(lambda x: data)
        self.assertEqual(cached.data, data)

    def test_gen_invalidated(self):
        """
        Cache should return the value generated, also after cache is invalidated
        """
        TestCached.invalidate()
        data1 = "First data"
        cached1 = TestCached(lambda x: data1)
        self.assertEqual(cached1.data, data1)

        # Repeat, to ensure invalidate works correctly too
        TestCached.invalidate()
        data2 = "Second data"
        cached2 = TestCached(lambda x: data2)
        self.assertEqual(cached2.data, data2)

    def test_cache_stores_value(self):
        """
        Cache should store the generated value
        """
        data1 = "Correct data"
        cached1 = TestCached(lambda x: data1)
        self.assertEqual(cached1.data, data1)

        cached2 = TestCached(lambda x: "Ignored data")
        self.assertEqual(cached2.data, data1)

    def test_invalidate(self):
        """
        If cache is invalidated during a data generation, then the data should not be cached.
        """
        data1 = "Wrong data"

        def create(data): # pylint: disable=unused-argument
            TestCached.invalidate()
            return data1

        # thread 1 starts to create some data
        cached1 = TestCached(create) # pylint: disable=unused-variable
        # thread 2 invalidates the cache (in create)
        # thread 1 completes data generation
        # thread 3 retrieves empty cache, thus generates new data
        data3 = "Correct data"
        cached3 = TestCached(lambda x: data3)
        self.assertEqual(cached3.data, data3)

    def test_out_of_order_update(self):
        """
        Cached should store the data, which generation was started at the latest point in time.
        """
        # thread 1 starts to create some data
        # thread 2 starts and sets data to someting else
        # thread 1 completes data generation
        # thread 3 reads data from thread 2
        data1 = "Wrong data"
        data2 = "Correct Data"

        def create(data): # pylint: disable=unused-argument
            cached2 = TestCached(lambda x: data2) # pylint: disable=unused-variable
            return data1

        cached1 = TestCached(create) # pylint: disable=unused-variable
        cached3 = TestCached(lambda x: "Ignored")
        self.assertEqual(cached3.data, data2)

    def test_latest_data(self):
        """
        Cached should store the data, which generation was started at the latest point in time.
        """
        def create_generator(event, sync, data):
            def generator(_old_data):
                sync.wait()
                event.wait()
                return data
            return generator

        def create_thread(func):
            def run():
                with cache_patcher() as cache: # pylint: disable=unused-variable
                    cached = TestCached(func) # pylint: disable=unused-variable
            th = Thread(target=run)
            th.start()
            return th
        # thread 1 starts to create some data
        event1 = Event()
        sync1 = Barrier(2, timeout=1)
        data1 = "Wrong data"
        t1 = create_thread(create_generator(event1, sync1, data1))
        sync1.wait()
        # thread 2 starts to create some data
        event2 = Event()
        sync2 = Barrier(2, timeout=1)
        data2 = "Correct data"
        t2 = create_thread(create_generator(event2, sync2, data2))
        sync2.wait()
        # thread 1 completes and stores data
        event1.set()
        t1.join()
        # thread 2 completes and stores updated data
        event2.set()
        t2.join()
        # thread 3 reads data from thread 2
        cached3 = TestCached(lambda x: "Ignored data")
        self.assertEqual(cached3.data, data2)
