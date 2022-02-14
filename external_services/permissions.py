from django.utils.translation import gettext_lazy as _

from authorization.permissions import Permission, ObjectVisibleBasePermission
from .models import MenuItem, LTIService


class MenuVisiblePermission(ObjectVisibleBasePermission):
    message = _('MENU_VISIBILTY_PERMISSION_DENIED_MSG')
    model = MenuItem
    obj_var = 'menu_item'

    def is_object_visible(self, request, view, menu_item):
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

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, view.menu_item)

    def has_object_permission(self, request, view, obj):
        return (obj.service
            and isinstance(obj.service, LTIService))
