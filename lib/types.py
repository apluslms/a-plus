from typing import Any, Dict, List, Type, TypeVar
from lib.helpers import empty_at_runtime

from django.db.models import Model
from django.forms import BoundField
from django.http import HttpRequest, HttpResponse

from rest_framework.request import Request
from rest_framework.serializers import Serializer


@empty_at_runtime
class SupportsDispatch:
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse: ...


@empty_at_runtime
class SupportsGetAccessMode:
    def get_access_mode(self) -> int: ...


@empty_at_runtime
class SupportsGetCommonObjects:
    def get_common_objects(self) -> None: ...


@empty_at_runtime
class SupportsGetContextData:
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]: ...


@empty_at_runtime
class SupportsGetFields:
    def get_fields(self, *names: str) -> List[BoundField]: ...


@empty_at_runtime
class SupportsGetObjectOrNone:
    TModel = TypeVar('TModel', bound=Model)
    def get_object_or_none(self, kwarg: str, model: Type[TModel], field: str = 'pk', **extra: Any) -> TModel: ...


@empty_at_runtime
class SupportsGetResourceObjects:
    def get_resource_objects(self) -> None: ...


@empty_at_runtime
class SupportsGetSerializerClass:
    def get_serializer_class(self) -> Type[Serializer]: ...


@empty_at_runtime
class SupportsGetUrlKwargs:
    def get_url_kwargs(self) -> Dict[str, Any]: ...


@empty_at_runtime
class SupportsHandleException:
    def handle_exception(self, exc: Exception) -> HttpResponse: ...


@empty_at_runtime
class SupportsHandleNoPermission:
    def handle_no_permission(self) -> HttpResponse: ...


@empty_at_runtime
class SupportsInitial:
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None: ...


@empty_at_runtime
class SupportsNote:
    def note(self, *args: str) -> None: ...


@empty_at_runtime
class SupportsValidateRequest:
    def validate_request(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None: ...
