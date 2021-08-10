from typing import Any, Dict

from django.http import Http404

from rest_framework.request import Request

from lib.helpers import object_at_runtime
from ..views import ResourceMixin


@object_at_runtime
class _ApiResourceMixinBase:
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None: ...


class ApiResourceMixin(ResourceMixin, _ApiResourceMixinBase):
    kwargs: Dict[str, Any]

    def initial(self, request, *args, **kwargs):
        """
        Call .get_resource_objects before .initial()
        Call .get_common_objects() after .initial()

        This is identical to validate_request, except .initial is used
        in rest_framework instead of validate_request
        """
        self.get_resource_objects()
        super().initial(request, *args, **kwargs)
        self.get_common_objects()

    def get_member_object(self, key, name):
        obj = getattr(self, key, None)
        if obj is None:
            raise Http404("%s not found." % (name,))
        return obj

    def get_object_or_none(self, kwarg, model, field='pk', **extra):
        val = self.kwargs.get(kwarg, None)
        if val is None:
            return None
        try:
            filters = {field: val}
            filters.update(extra)
            return model.objects.get(**filters)
        except model.DoesNotExist:
            return None

