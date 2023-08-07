from __future__ import annotations
import threading
from typing import Callable, Optional, Set, Type, TypeVar

from django.http import HttpRequest, HttpResponse


_global_types: Set[Type[ThreadGlobal]] = set()
# Each thread has their own object, so there is no possibility of two requests
# trying to access it at the same time
_global_store = threading.local()


T = TypeVar("T", bound="ThreadGlobal")
def set_global(cls: Type[T], obj: Optional[T]):
    setattr(_global_store, cls._unique_key, obj)


def get_global(cls: Type[ThreadGlobal]):
    return getattr(_global_store, cls._unique_key, None)


class ThreadGlobalMeta(type):
    _unique_key: str
    ABSTRACT: bool

    def __new__(cls, name, bases, namespace, **kwargs):
        ncls = super().__new__(cls, name, bases, namespace, **kwargs)
        if not ncls.__dict__.get("ABSTRACT", False):
            _global_types.add(ncls) # type: ignore
            ncls._unique_key = str(hash(ncls))
        return ncls


class ThreadGlobal(metaclass=ThreadGlobalMeta):
    ABSTRACT = True

    def init(self):
        """Called once when the object is first created"""

    def __new__(cls):
        obj = get_global(cls)

        if obj is None:
            obj = super().__new__(cls)
            obj.init()

        return obj

    def activate(self) -> None:
        set_global(self.__class__, self)

    @classmethod
    def deactivate(cls) -> None:
        set_global(cls, None)

    @staticmethod
    def clear_globals():
        for cls in _global_types:
            cls.deactivate()


class RequestGlobal(ThreadGlobal):
    """Any class inheriting from this class with ABSTRACT=False will have
    a request specific global variable set that is initialized with no arguments.

    For example,
    class Example(RequestGlobal):
        ABSTRACT=False
    causes a global to be initialized to Example(). The global can be accessed
    simply with Example(), that is all calls to Example() will return the same
    object that was initialized to the cache.

    The `__init__` method is called every time the object is accessed, i.e. the
    `__init__` method might be called multiple times for each object. Override
    the `init` method to initialize only once when the object is created.
    """
    ABSTRACT = True
    def init(self):
        """Called once when the object is first created"""

    def __new__(cls):
        obj = super().__new__(cls)
        obj.activate()
        return obj


class ClearRequestGlobals:
    """Middleware that clears RequestGlobal variables from thread local storage."""
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        RequestGlobal.clear_globals() # Just in case
        response = self.get_response(request)
        RequestGlobal.clear_globals()
        return response

    def process_exception(self, _request: HttpRequest, _exception: Exception) -> None:
        RequestGlobal.clear_globals()
