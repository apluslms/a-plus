from __future__ import annotations
from copy import deepcopy
from dataclasses import InitVar
from datetime import datetime
import itertools
from time import time
from typing import (
    Any,
    ClassVar,
    Dict,
    get_args,
    get_origin,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TYPE_CHECKING,
    TypeVar,
)
import logging
import sys

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

    def has_models(self, cls: Type[ModelT]) -> bool:
        """Return whether any objects of type cls are contained"""
        return cls.__name__ in self.data

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


PrecreatedProxies = Dict[Tuple[str,Tuple[Any, ...]], "CacheBase"]


CacheBaseT = TypeVar("CacheBaseT", bound="CacheBase")
def get_or_create_proxy(precreated: Optional[PrecreatedProxies], cls: Type[CacheBaseT], *params: Any) -> CacheBaseT:
    """
    Return proxy object corresponding to cls and params from precreated or create a new proxy object if
    not found otherwise.
    """
    proxy: Optional[CacheBaseT] = None
    if precreated:
        proxy = precreated.get((cls.KEY_PREFIX, params)) # type: ignore
    if proxy is None:
        proxy = cls.proxy(*params)
    return proxy


def get_or_set_precreated(precreated: PrecreatedProxies, proxy: CacheBase) -> None:
    precreated_proxy = precreated.setdefault((proxy.KEY_PREFIX, proxy._params), proxy)
    proxy.__dict__ = precreated_proxy.__dict__


def resolve_proxies(
        proxies: Iterable[CacheBase],
        precreated_proxies: Optional[Iterable[CacheBase]] = None,
        prefetched_data: Optional[DBData] = None,
        ) -> None:
    """
    Fetches the data from the cache and assigns it to the objects.
    Generates data for those that are invalid.
    """
    if precreated_proxies:
        all_proxies = itertools.chain(proxies, precreated_proxies)
    else:
        all_proxies = proxies

    precreated = {}
    for proxy in all_proxies:
        precreated_proxy = precreated.setdefault((proxy.KEY_PREFIX, proxy._params), proxy)
        proxy.__dict__ = precreated_proxy.__dict__

    proxies = [proxy for proxy in proxies if not proxy._resolved]

    keys = {proxy._cache_key for proxy in proxies}
    items = {k: v[1] for k,v in cache.get_many(keys).items()}

    new_states = {}
    for proxy in proxies:
        nstate = proxy._build(items, precreated, prefetched_data)
        if nstate:
            new_states[proxy._cache_key] = (proxy._generated_on, nstate)

    save_states = {}
    stored_states = cache.get_many(new_states.keys())
    for k, nstate in new_states.items():
        stored_state = stored_states.get(k)
        if (
            stored_state is None
            or stored_state[0] <= nstate[0]
        ):
            save_states[k] = nstate

    failed = cache.set_many(save_states)
    if failed:
        logger.warning(f"Failed to save the following in the cache: {'; '.join(failed)}")


def _dc(obj, memo):
    if id(obj) in memo:
        return memo[id(obj)]
    if isinstance(obj, dict):
        return {
            k: _dc(v, memo)
            for k,v in obj.items()
        }
    elif isinstance(obj, list):
        return [
            _dc(v, memo) for v in obj
        ]
    else:
        return deepcopy(obj, memo)


if TYPE_CHECKING:
    # This makes NoCache[T] look like T to type checkers
    NoCache = ClassVar
else:
    # NoCache[T] is swapped with T in annotations by CacheMeta
    from typing import Generic
    NotCached = TypeVar("NotCached")
    class NoCache(Generic[NotCached]): ...


class CacheMeta(type):
    """A metaclass for CacheBase to set the _cached_fields attribute automatically for each subclass"""
    _cached_fields: Tuple[str, ...]

    def __new__(cls, name, bases, namespace, **kwargs):
        ncls = super().__new__(cls, name, bases, namespace, **kwargs)

        globals = sys.modules[ncls.__module__].__dict__.copy()
        globals[ncls.__name__] = ncls

        cached_fields = set()
        annotations = ncls.__dict__.get('__annotations__', {})
        for k, ty in annotations.items():
            # get_type_hints returns base class annotations as well but we dont want those.
            # That also causes issues when the baseclasses use types that aren't imported
            # in the current class' module. Easier to just resolve the types ourselves.
            # This is how typing._eval_type resolves the type annotations
            if ty is None:
                ty = type(None)
            if isinstance(ty, str):
                ty = eval(ty, globals, namespace)

            origin = get_origin(ty)
            if origin is NoCache:
                # Remove NoCache from annotations
                ncls.__annotations__[k] = get_args(ty)[0]
            elif origin is not ClassVar and not isinstance(ty, InitVar):
                # Add non-NoCache and non-ClassVar to cached fields list
                cached_fields.add(k)

        sorted_fields = sorted(cached_fields.union(*(getattr(base, "_cached_fields", []) for base in bases)))
        # Would use a set but we need the order of the keys to always be the same for caching to work correctly
        ncls._cached_fields = tuple(sorted_fields)

        return ncls


T = TypeVar("T", bound="CacheBase")
class CacheBase(metaclass=CacheMeta):
    KEY_PREFIX = 'cache_base'
    _cache_key: NoCache[str]
    _resolved: NoCache[bool]
    _params: Tuple[Any, ...]
    _generated_on: float

    def __deepcopy__(self, memo):
        obj = self.__class__.__new__(self.__class__)
        memo[id(self)] = obj
        proxy_keys = self.get_proxy_keys()
        obj.__dict__ = {
            k: _dc(v, memo) if k in proxy_keys else deepcopy(v, memo)
            for k,v in self.__dict__.items()
        }
        return obj

    def post_get(self, precreated: PrecreatedProxies):
        """
        Called after the object was loaded from cache. Child proxies of self
        are just the _params tuple instead of the actual objects. This method
        must replace the child proxy tuples with actual objects. Get the object
        from precreated or create a new proxy if not found inside it (see the
        get_or_create_proxy function).
        """
        raise NotImplementedError()

    def is_valid(self) -> bool:
        return True

    def populate_children(self, prefetched_data: Optional[DBData] = None):
        children = self.get_child_proxies()
        resolve_proxies(children, prefetched_data=prefetched_data)

    def get_child_proxies(self) -> Iterable[CacheBase]:
        return []

    def get_proxy_keys(self) -> Iterable[str]:
        return []

    def as_proxy(self: T) -> T:
        return self.proxy(*self._params)

    def __getstate__(self):
        memo: Dict[int, tuple] = {}
        def as_proxy(obj: CacheBase) -> tuple:
            nonlocal memo
            proxy = memo.get(id(obj.__dict__))
            if proxy is None:
                proxy = obj._params
                memo[id(obj.__dict__)] = proxy

            return proxy

        proxy_keys = self.get_proxy_keys()
        state = self.__dict__
        values = []
        for key in self.__class__._cached_fields:
            if key not in proxy_keys:
                values.append(state[key])
                continue

            obj = state[key]
            if isinstance(obj, dict):
                nobj = obj.copy()
                for k,v in nobj.items():
                    if isinstance(v, CacheBase):
                        nobj[k] = as_proxy(v)
                values.append(nobj)
            elif isinstance(obj, list):
                values.append([as_proxy(v) if isinstance(v, CacheBase) else v for v in obj])
            elif isinstance(obj, tuple):
                values.append(tuple(as_proxy(v) if isinstance(v, CacheBase) else v for v in obj))
            elif isinstance(obj, CacheBase):
                values.append(as_proxy(obj))
            else:
                values.append(obj)

        return tuple([*values, self.__class__])

    def __setstate__(self, data: Any):
        cls = data[-1]
        self.__class__ = cls
        objdict = self.__dict__
        objdict["_resolved"] = True
        for name, value in zip(cls._cached_fields, data):
            objdict[name] = value

    def __getattr__(self, name: str) -> Any:
        if not self._resolved and name in self.__class__._cached_fields:
            logger.debug(f"Lazy resolving {self!r} due to missing {name}")
            resolve_proxies([self])
            return getattr(self, name)

        raise AttributeError(f"{name} not found in {self!r}")

    def __repr__(self):
        out = f"{self.__class__.__name__}("
        if self._resolved:
            out += f"generated_on={self.__dict__.get('_generated_on')}"
        else:
            out += f"resolved={self.__dict__.get('_resolved')}"
        return out + f", params={self.__dict__.get('_params')})"

    @classmethod
    def proxy(cls: Type[T], *params) -> T:
        obj = cls.__new__(cls)
        obj._resolved = False
        obj._params = params
        obj._cache_key = cls._key(*params)
        return obj

    @classmethod
    def get_for_models(cls: Type[T], *models, prefetch_children: bool = False, prefetched_data: Optional[DBData] = None) -> T:
        params = cls.parameter_ids(*models)
        return cls.get(*params, prefetch_children=prefetch_children, prefetched_data=prefetched_data)

    @classmethod
    def get(cls: Type[T], *params, prefetch_children: bool = False, prefetched_data: Optional[DBData] = None) -> T:
        cache_key = cls._key(*params)

        obj = cls.proxy(*params)

        data = cache.get(cache_key)
        if data is None or not isinstance(data, tuple):
            data = {}
        else:
            data = {cache_key: data[1]}

        nstate = obj._build(data, {}, prefetched_data)
        if nstate:
            stored_obj = cache.get(cache_key)
            if (
                stored_obj is None
                or stored_obj[0] <= obj._generated_on
            ):
                cache.set(cache_key, (obj._generated_on, nstate))

        if prefetch_children:
            obj.populate_children(prefetched_data)

        return obj

    @classmethod
    def _key(cls, *params) -> str:
        id_str = ','.join(str(p) for p in params)
        return f"{cls.KEY_PREFIX}:{id_str}"

    @classmethod
    def invalidate(cls, *models):
        cache_key = cls._key(*cls.parameter_ids(*models))
        logger.debug(f"Invalidating cached data for {cls.__name__}[{cache_key}]")
        # The cache is invalid, if the time field is None
        # The invalidation time is stored in the data field for debug messages
        # Keep this value in the cache for an hour, so it will be removed from
        # the memory at some point, but not before all generations have finished.
        cache.set(cache_key, (time(), None))

    def _build(
            self,
            cache_data: Dict[str, Any],
            precreated: PrecreatedProxies,
            prefetched_data: Optional[DBData],
            ) -> Optional[Tuple[Any, ...]]:
        attrs = cache_data.get(self._cache_key)
        if attrs is not None:
            try:
                self.__setstate__(attrs)
            except TypeError as e:
                logger.warning(f"__setstate__ TypeError with {self.__class__.__name__}[{self._cache_key}]: {e}")
                attrs = None # Generate new cache data
            else:
                self.post_get(precreated)

        if attrs is None or not self.is_valid():
            self._get_data(precreated, prefetched_data)
            return self.__getstate__()

        return None

    def _get_data(
            self,
            precreated: Optional[PrecreatedProxies] = None,
            prefetched_data: Optional[DBData] = None,
            ):
        if prefetched_data is None:
            gen_start = time()
        else:
            gen_start = prefetched_data.gen_start
        gen_start_dt = str(datetime.fromtimestamp(gen_start))
        cache_name = "%s[%s]" % (self.__class__.__name__, self._cache_key)
        logger.debug("Generating cached data for %s with ts %s", cache_name, gen_start_dt)
        self._generate_data(precreated=precreated, prefetched_data=prefetched_data)
        self._generated_on = gen_start
        self._resolved = True

    @classmethod
    def parameter_ids(cls, *models: Any) -> Tuple[Any, ...]:
        """Turn the cache parameters used to generate the data into ids that can be used to identify the original objects"""
        return tuple(getattr(model, "id", model) for model in models)

    def _generate_data(self, precreated: Optional[PrecreatedProxies] = None, prefetched_data: Optional[DBData] = None):
        raise NotImplementedError(f"Subclass of CacheBase ({self.__class__.__name__}) needs to implement _generate_data")
