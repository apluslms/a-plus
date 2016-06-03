"""
Base permission classes.

These classes use same interface than ones in django-rest-framework and
are usable with APIViews too. We define our superclass so we don't need to
depend on django-rest-framework.
"""

class Permission(object):
    """
    Permission interface
    """
    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        raise NotImplementedError

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        raise NotImplementedError


class NoPermission(Permission):
    """
    Base Permission class that gives no access permission to anyone.
    """
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False