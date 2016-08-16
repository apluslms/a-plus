from authorization.permissions import Permission, FilterBackend

from .models import UserProfile

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
