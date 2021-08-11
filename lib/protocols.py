from typing import Any, Dict, List, Protocol, Type, TypeVar
from lib.helpers import object_at_runtime

from django.db.models import Model
from django.forms import BoundField
from django.http import HttpRequest, HttpResponse

from rest_framework.request import Request
from rest_framework.serializers import Serializer


@object_at_runtime
class SupportsDispatch(Protocol):
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse: ...


@object_at_runtime
class SupportsGetAccessMode(Protocol):
    def get_access_mode(self) -> int: ...


@object_at_runtime
class SupportsGetCommonObjects(Protocol):
    def get_common_objects(self) -> None: ...


@object_at_runtime
class SupportsGetContextData(Protocol):
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]: ...


@object_at_runtime
class SupportsGetFields(Protocol):
    def get_fields(self, *names: str) -> List[BoundField]: ...


@object_at_runtime
class SupportsGetObjectOrNone(Protocol):
    TModel = TypeVar('TModel', bound=Model)
    def get_object_or_none(self, kwarg: str, model: Type[TModel]) -> TModel: ...


@object_at_runtime
class SupportsGetResourceObjects(Protocol):
    def get_resource_objects(self) -> None: ...


@object_at_runtime
class SupportsGetSerializerClass(Protocol):
    def get_serializer_class(self) -> Type[Serializer]: ...


@object_at_runtime
class SupportsGetUrlKwargs(Protocol):
    def get_url_kwargs(self) -> Dict[str, Any]: ...


@object_at_runtime
class SupportsHandleException(Protocol):
    def handle_exception(self, exc: Exception) -> HttpResponse: ...


@object_at_runtime
class SupportsHandleNoPermission(Protocol):
    def handle_no_permission(self) -> HttpResponse: ...

@object_at_runtime
class SupportsInitial(Protocol):
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None: ...


@object_at_runtime
class SupportsNote(Protocol):
    def note(self, *args: str) -> None: ...


@object_at_runtime
class SupportsValidateRequest(Protocol):
    def validate_request(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None: ...
