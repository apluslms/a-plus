from __future__ import annotations
from dataclasses import InitVar
from datetime import datetime
import pickle
from time import time
from typing import (
    Any,
    cast,
    ClassVar,
    Dict,
    get_args,
    get_origin,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
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


ProxyID = Tuple[str, Tuple[Any, ...], Tuple[Any, ...]]
CacheBaseT = TypeVar("CacheBaseT", bound="CacheBase")
class ProxyManager:
    proxies: Dict[ProxyID, CacheBase]
    fetched_data: Dict[str, Optional[bytes]]
    new_keys: Set[str]
    nstates: Dict[str, Tuple[float, bytes]]

    def __init__(self, proxies: Iterable[CacheBase] = ()):
        self.fetched_data = {}
        self.proxies = {}
        self.nstates = {}
        self.new_keys = set()
        self.update(proxies)

    def fetch(self) -> None:
        if self.new_keys:
            items = cast(Dict[str, Tuple[float, Optional[bytes]]], cache.get_many(self.new_keys))
            self.fetched_data.update((k, item[1]) for k,item in items.items())
            self.new_keys.clear()

    def update(self, proxies: Iterable[CacheBase] = ()) -> None:
        self.proxies.update({
            (proxy.KEY_PREFIX, proxy._params, proxy._modifiers): proxy
            for proxy in proxies
        })
        self.new_keys.update(key for proxy in proxies for key in proxy._keys)

    def resolve(self, proxies: Iterable[CacheBase], prefetched_data: Optional[DBData] = None) -> None:
        self.fetch()

        fetched = self.fetched_data
        nstates = self.nstates
        for proxy in proxies:
            if not proxy._resolved:
                proxy._build(fetched, nstates, self, prefetched_data)

    def save(self) -> None:
        stored_states = cache.get_many(self.nstates.keys())
        save_states = {}
        for k, nstate in self.nstates.items():
            # stored_state is None or a (float (time), Optional[bytes])-tuple like values in self.nstates
            stored_state = stored_states.get(k)
            if (
                stored_state is None
                or stored_state[0] <= nstate[0]
            ):
                save_states[k] = nstate

        failed = cache.set_many(save_states)
        if failed:
            logger.warning(f"Failed to save the following in the cache: {'; '.join(failed)}")

        self.nstates = {}

    def get_or_create_proxy(self, cls: Type[CacheBaseT], *params: Any, modifiers: Tuple[Any,...] = ()) -> CacheBaseT:
        """
        Return proxy object corresponding to cls and params from precreated or create a new proxy object if
        not found otherwise.
        """
        proxy_id = (cls.KEY_PREFIX, params, modifiers)
        proxy = self.proxies.get(proxy_id)
        if proxy is None:
            proxy = cls.proxy(*params, modifiers=modifiers)
            self.proxies[proxy_id] = proxy
            self.new_keys.update(proxy._keys)
        return proxy # type: ignore


def resolve_proxies(proxies: Iterable[CacheBase]) -> None:
    """Resolve proxies and save any newly generated ones"""
    manager = ProxyManager(proxies)
    manager.resolve(proxies)
    manager.save()


if TYPE_CHECKING:
    # This makes NoCache[T] and Varies[T] look like T to type checkers
    NoCache = ClassVar
    Varies = ClassVar
else:
    # NoCache[T] is swapped with T in annotations by CacheMeta
    from typing import Generic
    CacheT = TypeVar("CacheT")
    class NoCache(Generic[CacheT]):
        """Do not add the field to the cache"""
    class Varies(Generic[CacheT]):
        """Add the field to the cache separately for each object in the inheritance tree"""


def get_cache_fields(cls) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    if not hasattr(cls, "__dict__"):
        return (), ()

    if "_cached_fields" in cls.__dict__:
        return cls.__dict__["_cached_fields"], cls.__dict__["_varying_fields"]

    nocache_fields = set()
    cached_fields = set()
    varying_fields = set()

    annotations = cls.__dict__.get('__annotations__', {})
    if annotations:
        m_globals = sys.modules[cls.__module__].__dict__.copy()
        m_globals[cls.__name__] = cls
        for k, ty in annotations.items():
            # get_type_hints returns base class annotations as well but we dont want those.
            # That also causes issues when the baseclasses use types that aren't imported
            # in the current class' module. Easier to just resolve the types ourselves.
            # This is how typing._eval_type resolves the type annotations
            if ty is None:
                ty = type(None)
            if isinstance(ty, str):
                # pylint: disable-next=eval-used
                ty = eval(ty, m_globals, cls.__dict__)

            origin = get_origin(ty)
            if origin is NoCache:
                nocache_fields.add(k)
                # Remove NoCache from annotations
                cls.__annotations__[k] = get_args(ty)[0]
            elif origin is not ClassVar and not isinstance(ty, InitVar):
                # Add non-NoCache and non-ClassVar to cached fields list
                cached_fields.add(k)
                if origin is Varies:
                    varying_fields.add(k)

    # Add the cache fields from parents that aren't loaded separately
    parents = cls.__dict__.get("_parents", ())
    for base in cls.__bases__:
        cached, varying = get_cache_fields(base)
        varying_fields.update(varying)

        if base in parents:
            continue

        cached_fields.update(cached)

    cached_fields -= nocache_fields
    varying_fields -= nocache_fields
    cached_fields.update(varying_fields)

    # Would use a set but we need the order of the keys in cached_fields to always be the same for caching
    # to work correctly
    return tuple(sorted(cached_fields)), tuple(varying_fields)


class CacheMeta(type):
    """A metaclass for CacheBase to set the _cached_fields attribute automatically for each subclass"""
    # Use PARENTS: Tuple[CacheMeta, ...] to manually determine the parent classes
    KEY_PREFIX: str
    NUM_PARAMS: int
    _cached_fields: Tuple[str, ...]
    _varying_fields: Tuple[str, ...]
    _all_cached_fields: Set[str]
    _parents: Tuple[Type[CacheBase], ...]

    def __new__(cls, name, bases, namespace, **kwargs):
        ncls = super().__new__(cls, name, bases, namespace, **kwargs)

        if "KEY_PREFIX" in ncls.__dict__ and "NUM_PARAMS" not in ncls.__dict__:
            raise ValueError(
                f"Instances (classes) of CacheMeta must have both KEY_PREFIX"
                " and NUM_PARAMS or neither. {name} is missing NUM_PARAMS."
            )
        elif "KEY_PREFIX" not in ncls.__dict__ and "NUM_PARAMS" in ncls.__dict__:
            raise ValueError(
                f"Instances (classes) of CacheMeta must have both KEY_PREFIX"
                " and NUM_PARAMS or neither. {name} is missing KEY_PREFIX"
            )

        cache_meta_mro: List[CacheMeta] = [base for base in ncls.__mro__ if isinstance(base, CacheMeta)]
        cached_mro: List[CacheMeta] = [base for base in cache_meta_mro if "KEY_PREFIX" in base.__dict__]

        if "PARENTS" in ncls.__dict__:
            parents = ncls.__dict__["PARENTS"]
            for base in parents:
                if not isinstance(base, CacheMeta) or "KEY_PREFIX" not in base.__dict__:
                    raise ValueError(f"{base} is not a valid cache parent of {ncls}")
            ncls._parents = tuple([*parents, ncls])
        else:
            skip = set()
            for base in ncls.__bases__:
                if "_parents" in base.__dict__:
                    base_parents = base.__dict__["_parents"]
                    skip.update(base2 for base2 in base.__bases__ if base2 not in base_parents)

            parents = []
            for base in reversed(cached_mro):
                if base not in skip:
                    parents.append(base)
            ncls._parents = tuple(parents)

        ncls._cached_fields, ncls._varying_fields = get_cache_fields(ncls)
        ncls._all_cached_fields = {f for c in ncls._parents for f in c._cached_fields}

        return ncls


T = TypeVar("T", bound="CacheBase")
class CacheBase(metaclass=CacheMeta):
    _keys_with_cls: NoCache[List[Tuple[Type[CacheBase], str]]]
    _keys: NoCache[List[str]]
    _resolved: NoCache[bool]
    _params: NoCache[Tuple[Any, ...]]
    _modifiers: NoCache[Tuple[Any, ...]]
    _generated_on: Varies[float]

    def post_get(self, precreated: ProxyManager):
        """
        Called after the object was loaded from cache. Child proxies of self
        are just the _params tuple instead of the actual objects, unless a
        parent class' _generate_data or post_get has changed them.

        This is just a useful hook, and does not have to be implemented.
        """

    def post_build(self, precreated: ProxyManager):
        """
        Called after the whole object has been built (each object in the inheritance
        tree has been loaded from the cache or generated). This method
        must replace the child proxy tuples with actual objects (if not done
        previously by _generate_data or post_get). Get the object from precreated
        or create a new proxy if not found inside it (see the get_or_create_proxy
        function).
        """

    def is_valid(self) -> bool:
        return True

    def populate_children(self, prefetched_data: Optional[DBData] = None):
        children = self.get_child_proxies()
        precreated = ProxyManager([self, *children])
        precreated.resolve(children, prefetched_data=prefetched_data)

    def get_child_proxies(self) -> Iterable[CacheBase]:
        return []

    def get_proxy_keys(self) -> Iterable[str]:
        return []

    def as_proxy(self: T) -> T:
        return self.proxy(*self._params, self._modifiers)

    def __getstate__(self):
        memo: Dict[int, tuple] = {}
        def as_proxy(obj: CacheBase) -> tuple:
            nonlocal memo
            proxy = memo.get(id(obj.__dict__))
            if proxy is None:
                proxy = (obj._params, obj._modifiers)
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
        if not self._resolved and name in self.__class__._all_cached_fields:
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
        return out + f", params={self.__dict__.get('_params')}, modifiers={self.__dict__.get('_modifiers')})"

    @classmethod
    def proxy(cls: Type[T], *params, modifiers=()) -> T:
        obj = cls.__new__(cls)
        obj._resolved = False
        obj._params = params
        obj._modifiers = modifiers
        obj._keys_with_cls = cls._get_keys_with_cls(*params)
        obj._keys = [a for _, a in obj._keys_with_cls]
        return obj

    @classmethod
    def get_for_models(cls: Type[T], *models, prefetch_children: bool = False, prefetched_data: Optional[DBData] = None) -> T:
        params = cls.parameter_ids(*models)
        return cls.get(*params, prefetch_children=prefetch_children, prefetched_data=prefetched_data)

    @classmethod
    def get(cls: Type[T], *params, modifiers=(), prefetch_children: bool = False, prefetched_data: Optional[DBData] = None) -> T:
        precreated = ProxyManager()
        obj = precreated.get_or_create_proxy(cls, *params, modifiers=modifiers)
        precreated.resolve([obj], prefetched_data=prefetched_data)

        if prefetch_children:
            children = obj.get_child_proxies()
            precreated.resolve(children, prefetched_data=prefetched_data)

        precreated.save()

        return obj

    @classmethod
    def _get_keys_with_cls(cls, *params) -> List[Tuple[Type[CacheBase], str]]:
        keys = []
        for p in cls._parents:
            id_str = ','.join(str(p) for p in params[:p.NUM_PARAMS])
            cache_key = f"{p.KEY_PREFIX}:{id_str}"
            keys.append((p, cache_key))
        return keys

    @classmethod
    def invalidate(cls, *models):
        _, cache_key = cls._get_keys_with_cls(*cls.parameter_ids(*models))[-1]
        logger.debug(f"Invalidating cached data for {cls.__name__}[{cache_key}]")
        # The cache is invalid, if the time field is None
        # The invalidation time is stored in the data field for debug messages
        # Keep this value in the cache for an hour, so it will be removed from
        # the memory at some point, but not before all generations have finished.
        cache.set(cache_key, (time(), None))

    def _build(
            self,
            cache_data: Dict[str, Any],
            new_cache_data: Dict[str, Tuple[float, bytes]],
            precreated: ProxyManager,
            prefetched_data: Optional[DBData],
            ):
        ocls = self.__class__
        base_cls = None

        # Set _resolved to true to make sure that _get_data doesn't accidentally trigger lazy resolving
        # or recursively try to resolve self again
        self._resolved = True
        for base_cls, cache_key in self._keys_with_cls:
            # Trick python to use the base_cls' versions of methods instead of the original class'.
            # This should ensure that _get_data (and _generate_data) work correctly even if self
            # is actually an instance of a different class.
            self.__class__ = base_cls

            attrs = cache_data.get(cache_key)
            if attrs is not None:
                try:
                    self.__setstate__(pickle.loads(attrs))
                except TypeError as e:
                    logger.warning(f"__setstate__ TypeError with {base_cls}[{cache_key}]: {e}")
                    attrs = None # Generate new cache data
                else:
                    self.post_get(precreated)

            if attrs is None or not self.is_valid():
                self._get_data(precreated, prefetched_data)
                new_cache_data[cache_key] = (self._generated_on, pickle.dumps(self.__getstate__()))

        # Do not reset the class back if _get_data/unpickler changed the type
        if self.__class__ is base_cls:
            self.__class__ = ocls

        self.post_build(precreated)

    def _get_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBData] = None,
            ):
        if prefetched_data is None:
            gen_start = time()
        else:
            gen_start = prefetched_data.gen_start
        gen_start_dt = str(datetime.fromtimestamp(gen_start))
        cache_name = "%s[%s]" % (self.__class__.__name__, self._params)
        logger.debug("Generating cached data for %s with ts %s", cache_name, gen_start_dt)
        self._generate_data(precreated=precreated, prefetched_data=prefetched_data)
        self._generated_on = gen_start

    @classmethod
    def parameter_ids(cls, *models: Any) -> Tuple[Any, ...]:
        """Turn the cache parameters used to generate the data into ids that can be used to identify the original objects"""
        return tuple(getattr(model, "id", model) for model in models)

    def _generate_data(self, precreated: ProxyManager, prefetched_data: Optional[DBData] = None):
        raise NotImplementedError(f"Subclass of CacheBase ({self.__class__.__name__}) needs to implement _generate_data")
