from authorization.permissions import SAFE_METHODS, Permission, FilterBackend

from .models import UserProfile, GraderUser, LTIServiceUser

class IsAdminOrUserObjIsSelf(Permission, FilterBackend):
    def is_super(self, user):
        return (
            user.is_staff or
            user.is_superuser or
            isinstance(user, GraderUser) # grader is considered admin
        )

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, UserProfile):
            return True

        user = request.user
        return user and (
            (user.id is not None and user.id == obj.user_id) or
            self.is_super(user)
        )

    def filter_queryset(self, request, queryset, view):
        user = request.user
        if issubclass(queryset.model, UserProfile) and not self.is_super(user):
            queryset = queryset.filter(user_id=user.id)
        return queryset


class GraderUserCanOnlyRead(Permission):
    def has_permission(self, request, view):
        return (
            not isinstance(request.user, GraderUser) or
            request.method in SAFE_METHODS
        )


class IsLTIServiceUser(Permission):
    def has_permission(self, request, view):
        return isinstance(request.user, LTIServiceUser)
