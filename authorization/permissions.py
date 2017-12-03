from django.utils.translation import string_concat, ugettext_lazy as _

try:
    from django.utils.text import format_lazy
except ImportError: # implemented in Django 1.11
    from django.utils.functional import lazy as _lazy
    def _format_lazy(format_string, *args, **kwargs):
        return format_string.format(*args, **kwargs)
    format_lazy = _lazy(_format_lazy, str)

from lib.helpers import Enum

"""
Base permission classes.

These classes use same interface than ones in django-rest-framework and
are usable with APIViews too. We define our superclass so we don't need to
depend on django-rest-framework.
"""


SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


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


class MessageMixin(object):
    """
    Adds easy way to specify what exactly caused the PermissionDenied
    """
    def error_msg(self, message: str, delim=None, format=None, replace=False):
        """
        Add extra text to self.message about the reason why permission
        was denied. Uses lazy object so the message string is evaluated
        only when rendered.

        If optional argument `format` is given, then it's used with format_lazy
        to format the message with the dictionary arguments from `format` arg.

        Optional argument `delim` can be used to change the string used to join
        self.message and `message`.

        If optional argument `replace` is true, then self.message is replaced with
        the `message`.
        """
        if delim is None:
            delim = ': '

        if format:
            message = format_lazy(message, **format)

        if replace:
            self.message = message
        else:
            assert 'message' not in self.__dict__, (
                "You are calling error_msg without replace=True "
                "after calling it with it firts. Fix your code by removing "
                "firts method call add replace=True to second method call too."
            )
            self.message = string_concat(self.message, delim, message)


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
    ('SUPERUSER', 100, _("Superuser of the service")),
)


class AccessModePermission(MessageMixin, Permission):
    """
    If view has access_mode that is not anonymous, then require authentication
    """
    message = _("Permission denied by access mode.")

    def has_permission(self, request, view):
        access_mode = view.get_access_mode()

        if access_mode == ACCESS.ANONYMOUS:
            return True
        if not request.user.is_authenticated():
            return False

        if access_mode >= ACCESS.SUPERUSER:
            return request.user.is_superuser

        if access_mode >= ACCESS.TEACHER:
            if not view.is_teacher:
                self.error_msg(_("Only course teachers shall pass."))
                return False

        elif access_mode >= ACCESS.ASSISTANT:
            if not view.is_course_staff:
                self.error_msg(_("Only course staff shall pass."))
                return False

        elif access_mode == ACCESS.ENROLLED:
            if not view.is_course_staff and not view.is_student:
                self.error_msg(_("Only enrolled students shall pass."))
                return False

        return True


# Object permissions
# ==================


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
