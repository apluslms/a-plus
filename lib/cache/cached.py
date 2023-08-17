from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import InitVar
from datetime import datetime
from io import BytesIO
import pickle
from time import time
from typing import (
    Any,
    Callable,
    cast,
    ClassVar,
    Collection,
    Dict,
    get_args,
    get_origin,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
import logging
import sys

from django.db.models import Model
from django.db.models.signals import ModelSignal

from .transact import CacheTransactionManager


logger = logging.getLogger('aplus.cached2')

class DBDataManager(ABC):
    @abstractmethod
    def fetch(self) -> None:
        """Fetch data from the database for the added cache entries"""

    @abstractmethod
    def add(self, proxy: CacheBase) -> None:
        """Add cache object to be fetched data for"""


# generation time, expiry time, dependency params, object state
CacheData = Union[Tuple[float, None, None, None], Tuple[float, Optional[float], Dict[str, List[str]], Any]]
ProxyID = Tuple[str, Tuple[Any, ...], Tuple[Any, ...]]
CacheBaseT = TypeVar("CacheBaseT", bound="CacheBase")
class ProxyManager:
    """Handles creating and building cache objects while trying to minimize
    the number of cache operations.

    proxies contains a list of proxies managed by this manager.
    fetched_data holds on to the data fetched from the cache.
    new_keys contains cache keys that were added to the manager since the
    last cache get.
    nstates contains new items to be saved to the cache on .save().
    """
    gen_start: float
    proxies: Dict[ProxyID, CacheBase]
    fetched_data: Dict[str, Optional[CacheData]]
    new_keys: Set[str]
    nstates: Dict[str, CacheData]
    new_proxies: List[CacheBase]
    db_managers: Dict[Type[DBDataManager], DBDataManager]

    def __init__(self, proxies: Iterable[CacheBase] = ()):
        self.gen_start = time()
        self.fetched_data = {}
        self.proxies = {}
        self.nstates = {}
        self.new_keys = set()
        self.new_proxies = []
        self.db_managers = {}
        self.update(proxies)

    def fetch(self) -> None: # noqa: MC0001
        if self.new_keys:
            def fetch(keys: Set[str], used: Set[str]):
                used.update(keys)
                items = CacheTransactionManager().get_many(keys)
                items = cast(Dict[str, Optional[CacheData]], items)
                dependencies = {}
                next_keys = set()
                # Get all dependencies
                for key in keys:
                    item = items.get(key)
                    if item is None:
                        items[key] = None
                        continue
                    if item[2] is None or (item[1] is not None and item[1] < self.gen_start):
                        items[key] = None
                        continue

                    if item[2]:
                        dependency_keys = []
                        for key_prefix, postfixes in item[2].items():
                            dependency_keys.extend(f"{key_prefix}:{postfix}" for postfix in postfixes)

                        dependencies[key] = dependency_keys
                        next_keys.update(k for k in dependency_keys if k not in used and k not in self.fetched_data)

                # Fetch dependencies
                if next_keys:
                    fetch(next_keys, used)

                # Check dependencies for validity
                for key, dkeys in dependencies.items():
                    g,*_ = cast(CacheData, items[key])
                    for k in dkeys:
                        dependency = items.get(k) or self.fetched_data.get(k)
                        if dependency is None or dependency[0] > g:
                            items[key] = None
                            break

                self.fetched_data.update(items)

            # Get data from cache and check dependencies
            fetch(self.new_keys, set())
            self.new_keys.clear()

        if self.new_proxies:
            # Add proxies to db data manager
            changed = set()
            for proxy in self.new_proxies:
                for bcls, key in proxy._keys_with_cls:
                    dbcls = bcls.__dict__.get("DBCLS")
                    if dbcls is None:
                        continue
                    if dbcls not in self.db_managers:
                        self.db_managers[dbcls] = dbcls()
                    if self.fetched_data.get(key) is None:
                        self.db_managers[dbcls].add(proxy)
                        changed.add(dbcls)

            # Fetch db data
            for dbcls in changed:
                self.db_managers[dbcls].fetch()

            self.new_proxies.clear()

    def update(self, proxies: Iterable[CacheBase] = ()) -> None:
        self.proxies.update({
            (proxy.KEY_PREFIX, proxy._params, proxy._modifiers): proxy
            for proxy in proxies
        })
        self.new_keys.update(key for proxy in proxies for key in proxy._keys)
        for proxy in proxies:
            proxy._manager = self

    def resolve(self, proxies: Iterable[CacheBase], depth: int = 1) -> None:
        """Resolve given proxies. Depth is how many layers (child proxies) down should be resolved. Negative depth
        means to resolve the whole proxy tree.

        NOTE: Doesn't resolve the children of already resolved proxies no matter the depth value."""
        while proxies:
            self.fetch()

            fetched = self.fetched_data
            nstates = self.nstates
            db_managers = self.db_managers
            for proxy in filter(lambda x: not x._resolved, proxies):
                proxy._build(fetched, nstates, self, db_managers)

            depth -= 1
            if depth == 0:
                break

            proxies = [child for proxy in proxies for child in proxy.get_child_proxies() if not child._resolved]

    def save(self) -> None:
        stored_states = CacheTransactionManager().get_many(self.nstates.keys())
        save_states = {}
        for k, nstate in self.nstates.items():
            # stored_state is None or a (float (time), Optional[bytes])-tuple like values in self.nstates
            stored_state = stored_states.get(k)
            if (
                stored_state is None
                or stored_state[0] <= nstate[0]
            ):
                save_states[k] = nstate

        CacheTransactionManager().set_many(save_states)
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
            self.new_keys.update(key for key in proxy._keys if key not in self.fetched_data)
            proxy._manager = self
            self.new_proxies.append(proxy)
        return proxy # type: ignore


def resolve_proxies(proxies: Sequence[CacheBase]) -> None:
    """Resolve proxies and save any newly generated ones"""
    if proxies:
        try:
            manager = proxies[0]._manager
        except AttributeError:
            manager = ProxyManager(proxies)
        manager.resolve(proxies)
        manager.save()


class Pickler(pickle.Pickler):
    """Custom pickler that returns persistent ids for cache objects"""
    def __init__(self):
        self.buf = BytesIO()
        super().__init__(self.buf)

    def persistent_id(self, obj: Any) -> Any:
        if isinstance(obj, CacheBase):
            return (obj.__class__, obj._params, obj._modifiers)
        return None

    def getvalue(self) -> bytes:
        return self.buf.getvalue()


class Unpickler(pickle.Unpickler):
    """Custom unpickler that resolves persistent ids for cache objects created by the above pickler
    using the given proxy manager. Cache objects with the same params and modifiers will be set to
    the same instance"""
    precreated: ProxyManager

    def __init__(self, precreated, data):
        self.buf = BytesIO(data)
        super().__init__(self.buf)
        self.precreated = precreated

    def persistent_load(self, pid: Any) -> Any:
        return self.precreated.get_or_create_proxy(pid[0], *pid[1], modifiers=pid[2])


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
    proto_bases = cls.__dict__.get("_proto_bases", ())
    for base in cls.__bases__:
        if base in proto_bases:
            continue

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


ParamGenerator = Callable[[Model], Iterator[Tuple[Any, ...]]]
ParamGeneratorWithKwargs = Tuple[ParamGenerator, Tuple[str,...]]
def _invalidator(cls: CacheMeta, attrs_or_generator: Union[Tuple[str,...], ParamGenerator, ParamGeneratorWithKwargs]):
    def attr_getter(instance, attr):
        if isinstance(attr, list):
            if attr:
                return attr_getter(getattr(instance, attr[0]), attr[1:])
            return instance
        return getattr(instance, attr)

    if isinstance(attrs_or_generator, tuple) and not callable(attrs_or_generator[0]): # attrs
        # pylint: disable-next=unused-argument
        def inner(sender, instance, **kwargs):
            params = (attr_getter(instance, attr) for attr in attrs_or_generator) # type: ignore
            cls.invalidate(*params)
    elif isinstance(attrs_or_generator, tuple): # generator with kwargs
        generator, input_kwargs = attrs_or_generator

        # pylint: disable-next=unused-argument
        def inner(sender, instance, **kwargs):
            kwargs = {k: kwargs[k] for k in input_kwargs if k in kwargs}
            param_list = []
            for params in generator(instance, **kwargs): # type: ignore
                if not isinstance(params, tuple):
                    params = (params,)
                param_list.append(params)
            cls.invalidate_many(param_list)
    else: # generator
        # pylint: disable-next=unused-argument
        def inner(sender, instance, **kwargs):
            param_list = []
            for params in attrs_or_generator(instance):
                if not isinstance(params, tuple):
                    params = (params,)
                param_list.append(params)
            cls.invalidate_many(param_list)

    return inner


class CacheMeta(type):
    """
    A metaclass for CacheBase to set the _cached_fields attribute automatically for each subclass

    Class variables:
    - KEY_PREFIX: prefix used for the cache key
    - NUM_PARAMS: number of cache parameters (i.e. the parameters given to CacheBase.get())
    - INVALIDATORS: A list of (Model, List[ModelSignal], ParamAttrsOrGenerator). Used to
    determine which database models invalidate the cache. See basetypes.py and points.py for examples on use.
    - PARENTS: Can be used to override the parent items in cache. In essence, this can be used to
    manually determine which parent classes should be fetched separately and which should be included in the
    this class' cache. (Classes in PARENTS will be fetched separately)
    - PROTO_BASES: Base classes that are to be handled as protocols: their fields are not included in the
    cache.
    - DBCLS: DBDataManager subclass to be used for fetching data from the database.
    """
    # Use PARENTS: Tuple[CacheMeta, ...] to manually determine the parent classes
    KEY_PREFIX: str
    NUM_PARAMS: int
    INVALIDATORS: List[
        Tuple[
            Type[Model],
            List[ModelSignal],
            Union[Tuple[str,...], ParamGenerator, ParamGeneratorWithKwargs]
        ]
    ]
    DBCLS: Optional[Type[DBDataManager]] = None
    _cached_fields: Tuple[str, ...]
    _varying_fields: Tuple[str, ...]
    _all_cached_fields: Set[str]
    _parents: Tuple[Type[CacheBase], ...]
    _proto_bases: Tuple[type, ...]

    # pylint: disable-next=too-many-locals
    def __new__(cls, name, bases, namespace, **kwargs):
        ncls = super().__new__(cls, name, bases, namespace, **kwargs)

        cacheable_classvars = ("KEY_PREFIX", "NUM_PARAMS", "INVALIDATORS")
        missing_classvars = [k for k in cacheable_classvars if k not in ncls.__dict__]
        is_cacheable = len(missing_classvars) != len(cacheable_classvars)

        if is_cacheable and missing_classvars:
            raise ValueError(
                f"Instances (classes) of CacheMeta must have all of {', '.join(cacheable_classvars)}"
                f" or none of them. {name} is missing {', '.join(missing_classvars)}."
            )

        cache_meta_mro: List[CacheMeta] = [base for base in ncls.__mro__ if isinstance(base, CacheMeta)]
        cached_mro: List[CacheMeta] = [base for base in cache_meta_mro if "KEY_PREFIX" in base.__dict__]

        ncls._proto_bases = ncls.__dict__.get("PROTO_BASES", ())

        if "PARENTS" in ncls.__dict__:
            parents = ncls.__dict__["PARENTS"]
            for base in parents:
                if not isinstance(base, CacheMeta) or "KEY_PREFIX" not in base.__dict__:
                    raise ValueError(f"{base} is not a valid cache parent of {ncls}")
                if base in ncls._proto_bases:
                    raise ValueError(f"{base} cannot be both in PROTO_BASES and PARENTS of {ncls}")
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

        if "INVALIDATORS" in ncls.__dict__:
            for model, signals, attrs in ncls.INVALIDATORS:
                invalidator = _invalidator(ncls, attrs)
                for signal in signals:
                    signal.connect(invalidator, sender=model, weak=False)

        return ncls

    def _get_key_postfix(cls, params) -> str:
        return ','.join(str(p) for p in params)

    def _get_keys_with_cls(cls, *params) -> List[Tuple[Type[CacheBase], str]]:
        keys = []
        for p in cls._parents:
            id_str = p._get_key_postfix(params[:p.NUM_PARAMS])
            cache_key = f"{p.KEY_PREFIX}:{id_str}"
            keys.append((p, cache_key))
        return keys

    def parameter_ids(cls, *models: Any) -> Tuple[Any, ...]:
        """Turn the cache parameters used to generate the data into ids that can be used
        to identify the original objects"""
        return tuple(getattr(model, "id", model) for model in models)

    def invalidate(cls, *models: Any) -> None:
        _, cache_key = cls._get_keys_with_cls(*cls.parameter_ids(*models))[-1]
        logger.debug("Invalidating cached data for %s[%s]", cls.__name__, cache_key)
        # The cache is invalid, if the invalidate time is greater than the generation time
        # The time is needed in case the cache is being generated at the same time:
        # otherwise the cache could be generated using old data and then saved, even though
        # that data was invalidated
        CacheTransactionManager().set(cache_key, (time(), None, None, None))

    def invalidate_many(cls, models_iterable: Collection[Tuple[Any,...]]) -> None:
        if len(models_iterable) == 0:
            return
        params_iterable = (cls.parameter_ids(*models) for models in models_iterable)
        cache_keys = [cls._get_keys_with_cls(*params)[-1][1] for params in params_iterable]
        logger.debug("Invalidating cached data for %s%s", cls.__name__, cache_keys)
        t = (time(), None, None, None)
        CacheTransactionManager().set_many({ key: t for key in cache_keys })


Dependencies = Dict[Type["CacheBase"], Iterable[Tuple[Any,...]]]
T = TypeVar("T", bound="CacheBase")
class CacheBase(metaclass=CacheMeta):
    _keys_with_cls: NoCache[List[Tuple[Type[CacheBase], str]]]
    _keys: NoCache[List[str]]
    _resolved: NoCache[bool]
    _params: NoCache[Tuple[Any, ...]]
    _modifiers: NoCache[Tuple[Any, ...]]
    _generated_on: Varies[float]
    _expires_on: Varies[Optional[float]]
    # This might not exist if the object wasn't created through a ProxyManager
    _manager: NoCache[ProxyManager]

    def __init__(self, *args, **kwargs):
        raise TypeError("CacheBase classes cannot be instantiated normally. Use .get(...) or .proxy(...) instead.")

    def post_get(self, precreated: ProxyManager):
        """
        Called after the object was loaded from cache. This is called for each
        separately cached object in the inheritance tree.

        This is just a useful hook, and does not have to be implemented.
        """

    def post_build(self, precreated: ProxyManager):
        """
        Called after the whole object has been built (each object in the inheritance
        tree has been loaded from the cache or generated).

        This is just a useful hook, and does not have to be implemented.
        """

    def is_valid(self) -> bool:
        return True

    def populate_children(self):
        children = self.get_child_proxies()
        self._manager.resolve(children)

    def get_child_proxies(self) -> Iterable[CacheBase]:
        return []

    def as_proxy(self: T) -> T:
        return self.proxy(*self._params, self._modifiers)

    def __getstate__(self):
        return (self._params, self._modifiers)

    def __setstate__(self, data: Any):
        self._setproxy(*data)

    def _getstate(self):
        state = self.__dict__
        values = [state[k] for k in self.__class__._cached_fields]
        values.append(self.__class__)
        return tuple(values)

    def _setstate(self, data: Any):
        cls = data[-1]
        self.__class__ = cls
        objdict = self.__dict__
        objdict["_resolved"] = True
        for name, value in zip(cls._cached_fields, data):
            objdict[name] = value

    def __getattr__(self, name: str) -> Any:
        if not self._resolved and name in self.__class__._all_cached_fields:
            logger.debug("Lazy resolving %r due to missing %s", self, name)
            resolve_proxies([self])
            return getattr(self, name)
        if name in self.__class__._all_cached_fields:
            logger.error("Lazy resolving loop for %r due to missing %s", self, name)

        raise AttributeError(f"{name} not found in {self!r}")

    def __repr__(self):
        out = f"{self.__class__.__name__}("
        if self._resolved:
            out += f"generated_on={self.__dict__.get('_generated_on')}"
        else:
            out += f"resolved={self.__dict__.get('_resolved')}"
        return out + f", params={self.__dict__.get('_params')}, modifiers={self.__dict__.get('_modifiers')})"

    def _setproxy(self, params, modifiers):
        self._resolved = False
        self._params = params
        self._modifiers = modifiers
        self._keys_with_cls = self.__class__._get_keys_with_cls(*params)
        self._keys = [a for _, a in self._keys_with_cls]

    @classmethod
    def proxy(cls: Type[T], *params, modifiers=()) -> T:
        obj = cls.__new__(cls)
        obj._setproxy(params, modifiers)
        return obj

    @classmethod
    def get(cls: Type[T], *all_params, prefetch_children: bool = False) -> T:
        params, modifiers = all_params[:cls.NUM_PARAMS], all_params[cls.NUM_PARAMS:]
        params = cls.parameter_ids(*params)
        return cls._get(params, modifiers, prefetch_children=prefetch_children)

    @classmethod
    def _get(
            cls: Type[T],
            params: Tuple[Any,...],
            modifiers: Tuple[Any,...] = (),
            prefetch_children: bool = False,
            ) -> T:
        precreated = ProxyManager()
        obj = precreated.get_or_create_proxy(cls, *params, modifiers=modifiers)
        precreated.resolve([obj])

        if prefetch_children:
            children = obj.get_child_proxies()
            precreated.resolve(children)

        precreated.save()

        return obj

    def _build(
            self,
            cache_data: Dict[str, Optional[CacheData]],
            new_cache_data: Dict[str, CacheData],
            precreated: ProxyManager,
            db_managers: Dict[Type[DBDataManager], DBDataManager],
            ):
        ocls = self.__class__
        base_cls = None

        # Set _resolved to true here to make sure that _get_data doesn't accidentally trigger lazy resolving
        # or recursively try to resolve self again
        self._resolved = True
        for base_cls, cache_key in self._keys_with_cls:
            # Trick python to use the base_cls' versions of methods instead of the original class'.
            # This should ensure that _get_data (and _generate_data) work correctly even if self
            # is actually an instance of a different class.
            self.__class__ = base_cls

            attrs = cache_data.get(cache_key)
            if attrs is not None and attrs[3] is None:
                attrs = None

            if attrs is not None:
                try:
                    unpickler = Unpickler(precreated, attrs[3])
                    self._setstate(unpickler.load())
                except TypeError as e:
                    logger.warning("_setstate TypeError with %s[%s]: %s", base_cls, cache_key, e)
                    attrs = None # Generate new cache data
                else:
                    self.post_get(precreated)

            if attrs is None or not self.is_valid():
                dependencies = self._get_data(precreated, db_managers.get(base_cls.__dict__.get("DBCLS")))
                dependencies = {
                    dcls.KEY_PREFIX: [dcls._get_key_postfix(params) for params in paramss]
                    for dcls,paramss in dependencies.items()
                }
                pickler = Pickler()
                pickler.dump(self._getstate())
                new_cache_data[cache_key] = (self._generated_on, self._expires_on, dependencies, pickler.getvalue())

        # Do not reset the class back if _get_data/unpickler changed the type
        if self.__class__ is base_cls:
            self.__class__ = ocls

        self.post_build(precreated)

    def _get_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBDataManager] = None,
            ) -> Dependencies:
        gen_start = precreated.gen_start
        gen_start_dt = str(datetime.fromtimestamp(gen_start))
        cache_name = "%s[%s]" % (self.__class__.__name__, self._params)
        logger.debug("Generating cached data for %s with ts %s", cache_name, gen_start_dt)
        self._expires_on = None
        dependencies = self._generate_data(precreated=precreated, prefetched_data=prefetched_data)
        if "_generated_on" not in self.__dict__:
            self._generated_on = gen_start
        else:
            self._generated_on = max(gen_start, self._generated_on)
        return dependencies or {}

    def _generate_data(
            self, precreated: ProxyManager, prefetched_data: Optional[DBDataManager]
            ) -> Optional[Dependencies]:
        """Generate the data for self. Use precreated to get/create/resolve any additional cache objects"""
        raise NotImplementedError(
            f"Subclass of CacheBase ({self.__class__.__name__}) needs to implement _generate_data"
        )
