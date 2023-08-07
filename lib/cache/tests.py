from typing import Optional
from django.db import transaction
from django.test import SimpleTestCase, TransactionTestCase
from threading import Thread, Event, Barrier
from unittest.mock import patch
from lib.cache.cached import DBData, ProxyManager

from lib.cache.cached_old import CachedAbstract
from .cached import CacheBase


mock_cache = {}

def mock_delete(key):
    mock_cache.pop(key, None)

def mock_set(key, value, timeout=None): # pylint: disable=unused-argument
    mock_cache[key] = value

def mock_get(key, default=None):
    return mock_cache.get(key, default)

def mock_get_many(keys):
    return {
        k: mock_cache[k]
        for k in keys
        if k in mock_cache
    }

def mock_set_many(items):
    mock_cache.update(items)

def mock_add(key, value, timeout=None): # pylint: disable=unused-argument
    if key not in mock_cache:
        mock_cache[key] = value
        return True
    return False


def cache_patcher(loc):
    return patch.multiple(f'lib.cache.{loc}.cache',
        add=mock_add, delete=mock_delete,
        get=mock_get, set=mock_set,
        get_many=mock_get_many, set_many=mock_set_many)


class Rollback(Exception): ...


class MockCache(CacheBase):
    KEY_PREFIX = "cachetest"
    NUM_PARAMS = 0
    INVALIDATORS = []

    def _generate_data(self, precreated: ProxyManager, prefetched_data: Optional[DBData] = None):
        return


@cache_patcher('transact')
class TransactionTest(TransactionTestCase):
    def test_rollback(self):
        original = MockCache.get()
        try:
            with transaction.atomic():
                MockCache.invalidate()
                new = MockCache.get()
                self.assertNotEqual(original._generated_on, new._generated_on)
                raise Rollback()
        except Rollback:
            pass

        original2 = MockCache.get()
        self.assertEqual(original._generated_on, original2._generated_on)

    def test_commit(self):
        original = MockCache.get()
        with transaction.atomic():
            MockCache.invalidate()
            new = MockCache.get()

            self.assertNotEqual(original._generated_on, new._generated_on)

        new2 = MockCache.get()
        self.assertEqual(new._generated_on, new2._generated_on)

    def test_no_transaction(self):
        original = MockCache.get()
        original2 = MockCache.get()
        self.assertEqual(original._generated_on, original2._generated_on)
        MockCache.invalidate()
        new = MockCache.get()
        self.assertNotEqual(original._generated_on, new._generated_on)

    def test_within_transaction(self):
        original = MockCache.get()
        with transaction.atomic():
            original2 = MockCache.get()
            self.assertEqual(original._generated_on, original2._generated_on)
            MockCache.invalidate()
            new = MockCache.get()
            self.assertNotEqual(original._generated_on, new._generated_on)

    def test_nested_transaction(self):
        original = MockCache.get()
        with transaction.atomic():
            MockCache.invalidate()
            new = MockCache.get()
            self.assertNotEqual(original._generated_on, new._generated_on)
            with transaction.atomic():
                MockCache.invalidate()
                newer = MockCache.get()
                self.assertNotEqual(new._generated_on, newer._generated_on)

            newer2 = MockCache.get()
            self.assertEqual(newer._generated_on, newer2._generated_on)

            try:
                with transaction.atomic():
                    MockCache.invalidate()
                    newerer = MockCache.get()
                    self.assertNotEqual(newer._generated_on, newerer._generated_on)
                    raise Rollback()
            except Rollback:
                pass

            newer3 = MockCache.get()
            self.assertEqual(newer._generated_on, newer3._generated_on)

        newer4 = MockCache.get()
        self.assertEqual(newer._generated_on, newer4._generated_on)

    def test_changed_during_transaction(self):
        original = []
        new = []
        newer = []
        newerer = []

        def t1():
            with transaction.atomic():
                original.append(MockCache.get())
                original.append(MockCache.get())
                syncs[0].wait()
                syncs[1].wait()
                # cache was invalidated in t2
                new.append(MockCache.get())
                new.append(MockCache.get())
                syncs[2].wait()
                syncs[3].wait()

            # newer[0] should be newer than t1 new. This results in a conflict
            # and it should have been invalidated on commit
            newerer.append(MockCache.get())

        def t2():
            syncs[0].wait()
            MockCache.invalidate()
            syncs[1].wait()
            syncs[2].wait()
            # t1 changes haven't been saved yet, so this generates a new object
            newer.append(MockCache.get())
            syncs[3].wait()

        syncs = [Barrier(2, timeout=1) for _ in range(4)]
        th = Thread(target=t1)
        th.start()
        th2 = Thread(target=t2)
        th2.start()
        th.join()
        th2.join()
        self.assertNotEqual(original[0]._generated_on, new[0]._generated_on)
        self.assertNotEqual(original[0]._generated_on, newer[0]._generated_on)
        self.assertNotEqual(original[0]._generated_on, newerer[0]._generated_on)
        self.assertNotEqual(new[0]._generated_on, newer[0]._generated_on)
        self.assertNotEqual(new[0]._generated_on, newerer[0]._generated_on)
        self.assertNotEqual(newer[0]._generated_on, newerer[0]._generated_on)
        for i, c in enumerate(original[1:]):
            self.assertEqual(original[0]._generated_on, c._generated_on, f"c = original[{i+1}]")
        for i, c in enumerate(new[1:]):
            self.assertEqual(new[0]._generated_on, c._generated_on, f"c = new[{i+1}]")
        for i, c in enumerate(newer[1:]):
            self.assertEqual(newer[0]._generated_on, c._generated_on, f"c = newer[{i+1}]")
        for i, c in enumerate(newerer[1:]):
            self.assertEqual(newerer[0]._generated_on, c._generated_on, f"c = newerer[{i+1}]")
        self.assertEqual(len(original), 2)
        self.assertEqual(len(new), 2)
        self.assertEqual(len(newer), 1)
        self.assertEqual(len(newerer), 1)

    def test_invalidating_transaction(self):
        original = []
        new = []

        def t1():
            original.append(MockCache.get())
            with transaction.atomic():
                MockCache.invalidate()
                syncs[0].wait()
                syncs[1].wait()
            # Invalidation is applied here
            syncs[2].wait()

        def t2():
            syncs[0].wait()
            # This is after t1 calls invalidate(), but the invalidation
            # hasn't been applied yet
            original.append(MockCache.get())
            syncs[1].wait()
            syncs[2].wait()
            new.append(MockCache.get())

        syncs = [Barrier(2, timeout=1) for _ in range(3)]
        th = Thread(target=t1)
        th.start()
        th2 = Thread(target=t2)
        th2.start()
        th.join()
        th2.join()
        self.assertNotEqual(original[0]._generated_on, new[0]._generated_on)
        for i, c in enumerate(original[1:]):
            self.assertEqual(original[0]._generated_on, c._generated_on, f"c = original[{i+1}]")
        for i, c in enumerate(new[1:]):
            self.assertEqual(new[0]._generated_on, c._generated_on, f"c = new[{i+1}]")
        self.assertEqual(len(original), 2)
        self.assertEqual(len(new), 1)

    def test_overridden_invalidate_transaction(self):
        original = []
        new = []

        def t1():
            original.append(MockCache.get())
            with transaction.atomic():
                MockCache.invalidate()
                syncs[0].wait()
                syncs[1].wait()
                new.append(MockCache.get())
            syncs[2].wait()

        def t2():
            syncs[0].wait()
            original.append(MockCache.get())
            syncs[1].wait()
            syncs[2].wait()
            # t1 generates a new one after invalidating: that should be the one saved to cache
            new.append(MockCache.get())

        syncs = [Barrier(2, timeout=1) for _ in range(3)]
        th = Thread(target=t1)
        th.start()
        th2 = Thread(target=t2)
        th2.start()
        th.join()
        th2.join()
        self.assertNotEqual(original[0]._generated_on, new[0]._generated_on)
        for i, c in enumerate(original[1:]):
            self.assertEqual(original[0]._generated_on, c._generated_on, f"c = original[{i+1}]")
        for i, c in enumerate(new[1:]):
            self.assertEqual(new[0]._generated_on, c._generated_on, f"c = new[{i+1}]")
        self.assertEqual(len(original), 2)
        self.assertEqual(len(new), 2)


class TestCached(CachedAbstract):
    def __init__(self, func):
        self._fake_func = func
        super().__init__()

    def _generate_data(self, *models, data=None):
        return self._fake_func(data)


@cache_patcher('cached_old')
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
                with cache_patcher('cached_old') as cache: # pylint: disable=unused-variable
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
