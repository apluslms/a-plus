from authorization.permissions import SAFE_METHODS, Permission, FilterBackend

from .models import UserProfile, GraderUser

class IsAdminOrUserObjIsSelf(Permission, FilterBackend):
    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, UserProfile):
            return True

        user = request.user
        return user and (
            user.is_staff or
            user.is_superuser or
            user.id == obj.user_id
        )


    def filter_queryset(self, request, queryset, view):
        user = request.user
        is_super = user.is_staff or user.is_superuser
        if issubclass(queryset.model, UserProfile) and not is_super:
            queryset = queryset.filter(user_id=user.id)
        return queryset


class GraderUserCanOnlyRead(Permission):
    def has_permission(self, request, view):
        return (
            not isinstance(request.user, GraderUser) or
            request.method in SAFE_METHODS
        )
