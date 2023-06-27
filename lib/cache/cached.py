from __future__ import annotations
from datetime import datetime
from time import time
from typing import Any, Tuple, Type, TypeVar
import logging

from django.core.cache import cache
from django.db.models import Model

logger = logging.getLogger('aplus.cached2')


T = TypeVar("T", bound="CacheBase")
class CacheBase:
    KEY_PREFIX = 'cache_base'
    _cache_key: str
    _generated_on: float

    def is_valid(self) -> bool:
        return True

    @classmethod
    def get_for_models(cls: Type[T], *models) -> T:
        params = cls.parameter_ids(*models)
        return cls.get(*params)

    @classmethod
    def get(cls: Type[T], *params) -> T:
        cache_key = cls._key(*params)

        obj = cache.get(cache_key)

        if isinstance(obj, tuple):
            obj = obj[1]
        if not isinstance(obj, cls) or not obj.is_valid():
            obj = None

        if obj is None:
            obj = cls._get_data(*params)

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
    def _get_data(cls: Type[T], *params) -> T:
        cache_key = cls._key(*params)
        gen_start = time()
        gen_start_dt = str(datetime.fromtimestamp(gen_start))
        cache_name = "%s[%s]" % (cls.__name__, cache_key)
        logger.debug("Generating cached data for %s with ts %s", cache_name, gen_start_dt)
        obj = cls._generate_data(*params)
        obj._generated_on = gen_start
        obj._cache_key = cache_key

        return obj

    @classmethod
    def parameter_ids(cls, *models: Any) -> Tuple[Any, ...]:
        """Turn the cache parameters used to generate the data into ids that can be used to identify the original objects"""
        return tuple(getattr(model, "id", model) for model in models)

    @classmethod
    def _generate_data(cls: Type[T], *params) -> T:
        raise NotImplementedError(f"Subclass of CacheBase ({cls.__name__}) needs to implement _generate_data")
