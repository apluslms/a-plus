from __future__ import annotations
from datetime import datetime
from time import time
from typing import Any, Dict, Iterable, Optional, Tuple, Type, TypeVar
import logging

from django.core.cache import cache
from django.db.models import Model

logger = logging.getLogger('aplus.cached2')


ModelT = TypeVar("ModelT", bound=Model)
class DBData:
    # Model_class.__name__ -> {Model_object.id -> Model_object}
    data: Dict[str, Dict[int, Any]]
    gen_start: float

    def __init__(self):
        self.gen_start = time()
        self.data = {}

    def add(self, obj: Model):
        container = self.data.setdefault(obj.__class__.__name__, {})
        container[obj.id] = obj

    def extend(self, cls: Type[ModelT], objects: Iterable[ModelT]):
        container = self.data.setdefault(cls.__name__, {})
        for obj in objects:
            container[obj.id] = obj

    def get_db_object(self: Optional[DBData], cls: Type[ModelT], model_id: int) -> ModelT:
        """
        Try to get an object from the prefeteched data, or get it from the database if not there.

        Works with self == None, so you can do DBData.get_db_object(maybe_None_DBData, ...).
        """
        if self:
            obj = self.data.get(cls.__name__, {}).get(model_id)
            if obj is not None:
                return obj
        return cls.objects.get(id=model_id)

    def filter_db_objects(self: Optional[DBData], cls: Type[ModelT], **search: Any) -> Iterable[ModelT]:
        """
        Search from prefetched_data if the prefetched data has data for the class, otherwise search from the database.

        Works with self == None, so you can do DBData.filter_db_objects(maybe_None_DBData, ...).
        WARNING: the returned data may not contain all of the matching objects if self.data contains some objects but
        not all of the relevant ones.
        """
        if self and cls.__name__ in self.data:
            objs = self.data[cls.__name__].values()
            found = []
            for obj in objs:
                for k,v in search.items():
                    if getattr(obj, k, None) != v:
                        break
                else:
                    found.append(obj)
            return found

        return cls.objects.filter(**search)

    def __bool__(self) -> bool:
        return bool(self.data)


T = TypeVar("T", bound="CacheBase")
class CacheBase:
    KEY_PREFIX = 'cache_base'
    _cache_key: str
    _generated_on: float

    def is_valid(self) -> bool:
        return True

    @classmethod
    def get_for_models(cls: Type[T], *models, prefetched_data: Optional[DBData] = None) -> T:
        params = cls.parameter_ids(*models)
        return cls.get(*params, prefetched_data=prefetched_data)

    @classmethod
    def get(cls: Type[T], *params, prefetched_data: Optional[DBData] = None) -> T:
        cache_key = cls._key(*params)

        obj = cache.get(cache_key)

        if isinstance(obj, tuple):
            obj = obj[1]
        if not isinstance(obj, cls) or not obj.is_valid():
            obj = None

        if obj is None:
            obj = cls._get_data(*params, prefetched_data=prefetched_data)

            stored_obj = cache.get(cache_key)
            if isinstance(stored_obj, tuple):
                stored_obj = stored_obj[0]
            if (
                stored_obj is None
                or not isinstance(stored_obj, float)
                or stored_obj <= obj._generated_on
            ):
                cache.set(cache_key, obj)

        return obj

    @classmethod
    def _key(cls, *params) -> str:
        id_str = ','.join(str(p) for p in params)
        return f"{cls.KEY_PREFIX}:{id_str}"

    @classmethod
    def invalidate(cls, *models):
        cache_key = cls._key(*cls.parameter_ids(*models))
        logger.debug("Invalidating cached data for %s", cache_key)
        # The cache is invalid, if the time field is None
        # The invalidation time is stored in the data field for debug messages
        # Keep this value in the cache for an hour, so it will be removed from
        # the memory at some point, but not before all generations have finished.
        cache.set(cache_key, time())

    @classmethod
    def _get_data(cls: Type[T], *params, prefetched_data: Optional[DBData] = None) -> T:
        cache_key = cls._key(*params)
        if prefetched_data is None:
            gen_start = time()
        else:
            gen_start = prefetched_data.gen_start
        gen_start_dt = str(datetime.fromtimestamp(gen_start))
        cache_name = "%s[%s]" % (cls.__name__, cache_key)
        logger.debug("Generating cached data for %s with ts %s", cache_name, gen_start_dt)
        obj = cls._generate_data(*params, prefetched_data=prefetched_data)
        obj._generated_on = gen_start
        obj._cache_key = cache_key

        return obj

    @classmethod
    def parameter_ids(cls, *models: Any) -> Tuple[Any, ...]:
        """Turn the cache parameters used to generate the data into ids that can be used to identify the original objects"""
        return tuple(getattr(model, "id", model) for model in models)

    @classmethod
    def _generate_data(cls: Type[T], *params, prefetched_data: Optional[DBData] = None) -> T:
        raise NotImplementedError(f"Subclass of CacheBase ({cls.__name__}) needs to implement _generate_data")
