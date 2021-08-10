from typing import Any, Dict, Optional, Type

from rest_framework.request import Request
from rest_framework.serializers import BaseSerializer

from lib.helpers import object_at_runtime


@object_at_runtime
class _ListSerializerMixinBase:
    def get_serializer_class(self) -> Type[BaseSerializer]: ...


class ListSerializerMixin(_ListSerializerMixinBase):
    action: str
    serializer_class: Optional[Type[BaseSerializer]]

    # FIXME: use rest_framework_extensions.mixins.DetailSerializerMixin
    def get_serializer_class(self):
        if self.action == 'list':
            return getattr(self, 'listserializer_class', self.serializer_class)
        return super(ListSerializerMixin, self).get_serializer_class()


@object_at_runtime
class _MeUserMixinBase:
    def initial(self, request: Request, *args: Any, **kwargs: Any): ...


class MeUserMixin(_MeUserMixinBase):
    kwargs: Dict[str, Any]
    me_user_url_kw = 'user_id'
    me_user_value = 'me'

    # Hook into `initial` method call chain.
    # after calling `initial` we have done all authentication related tasks,
    # so there is valid request.user also with token authentication
    # NOTE: self.kwargs is a pointer to the dict inside rest_framework / self.dispatch
    # and kwargs given to the initial is a copy of that dictionary.

    def initial(self, request, *args, **kwargs):
        super(MeUserMixin, self).initial(request, *args, **kwargs)

        kw = self.me_user_url_kw
        value = self.kwargs.get(kw, None)
        if value and self.me_user_value == value:
            self.kwargs[kw] = request.user.id if request.user.is_authenticated else None
