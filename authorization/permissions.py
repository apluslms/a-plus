from django.utils.translation import ugettext_lazy as _

from lib.helpers import Enum
from lib.messages import error as error_msg

"""
Base permission classes.

These classes use same interface than ones in django-rest-framework and
are usable with APIViews too. We define our superclass so we don't need to
depend on django-rest-framework.
"""

class FilterBackend(object):
    """
    FilterBackend interface
    """
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        raise NotImplementedError

    def get_fields(self, view):
        return []


class Permission(object):
    """
    Permission interface
    """
    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True


class NoPermission(Permission):
    """
    Base Permission class that gives no access permission to anyone.
    """
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


# Access mode
# ===========

# All access levels
ACCESS = Enum(
    ('ANONYMOUS', 0, _("Any user authenticated or not")),
    ('ENROLL', 1, None),
    ('STUDENT', 3, _("Any authenticated student")),
    ('ENROLLED', 4, _("Enrolled student of the course")),
    ('ASSISTANT', 5, _("Assistant of the course")),
    ('GRADING', 6, _("Grading. Assistant if course has that option or teacher")),
    ('TEACHER', 10, _("Teacher of the course")),
)


class AccessModePermission(Permission):
    """
    If view has access_mode that is not anonymous, then require authentication
    """
    message = _("Permission denied by access mode")

    def has_permission(self, request, view):
        access_mode = view.get_access_mode()

        if access_mode == ACCESS.ANONYMOUS:
            return True
        if not request.user.is_authenticated():
            return False

        if access_mode >= ACCESS.TEACHER:
            if not view.is_teacher:
                error_msg(request, _("Only course teachers shall pass."))
                return False

        elif access_mode >= ACCESS.ASSISTANT:
            if not view.is_course_staff:
                error_msg(request, _("Only course staff shall pass."))
                return False

        elif access_mode == ACCESS.ENROLLED:
            if not view.instance.is_student(request.user):
                error_msg(request, _("Only enrolled students shall pass."))
                return False

        return True


# Object permissions
# ==================


class MessageMixin(object):
    def error_msg(self, request, msg):
        self.message = msg
        error_msg(request, msg)


class ObjectVisibleBasePermission(MessageMixin, Permission):
    model = None
    obj_var = None

    def has_permission(self, request, view):
        obj = getattr(view, self.obj_var, None)
        return (
            obj is None or
            self.has_object_permission(request, view, obj)
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        return (
            not isinstance(obj, self.model) or # skip objects that are not model in question
            user.is_staff or
            user.is_superuser or
            self.is_object_visible(request, view, obj)
        )

    def is_object_visible(self, request, view, obj):
        raise NotImplementedError
