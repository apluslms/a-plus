from typing import Any, TYPE_CHECKING

from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _

from authorization.permissions import Permission, ObjectVisibleBasePermission
from .models import MenuItem, LTIService

if TYPE_CHECKING:
    from course.viewbase import CourseInstanceBaseMixin
    from external_services.views import LTILoginView


class MenuVisiblePermission(ObjectVisibleBasePermission[MenuItem]):
    message = _('MENU_VISIBILTY_PERMISSION_DENIED_MSG')
    model = MenuItem
    obj_var = 'menu_item'

    def is_object_visible(
            self,
            request: HttpRequest,
            view: 'CourseInstanceBaseMixin',
            menu_item: MenuItem,
            ) -> bool:
        if (not menu_item.enabled
                or (menu_item.service and not menu_item.service.enabled)):
            return False

        if menu_item.access >= MenuItem.ACCESS.TEACHER:
            if not view.is_teacher:
                self.error_msg(_('MENU_VISIBILITY_ERROR_ONLY_TEACHERS'))
                return False

        elif menu_item.access >= MenuItem.ACCESS.ASSISTANT:
            if not view.is_course_staff:
                self.error_msg(_('MENU_VISIBILITY_ERROR_ONLY_COURSE_STAFF'))
                return False

        return True


class LTIServicePermission(Permission):
    message = _('NOT_LTI_SERVICE')

    def has_permission(self, request: HttpRequest, view: 'LTILoginView') -> bool:
        return self.has_object_permission(request, view, view.menu_item)

    def has_object_permission(self, request: HttpRequest, view: Any, obj: MenuItem) -> bool:
        return (obj.service is not None
            and isinstance(obj.service.as_leaf_class(), LTIService))
