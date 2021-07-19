from typing import Any, cast

from django.contrib.auth.models import User
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from authorization.permissions import SAFE_METHODS, Permission, FilterBackend
from course.models import CourseInstance
from .models import UserProfile, GraderUser, LTIServiceUser

class IsAdminOrUserObjIsSelf(Permission, FilterBackend):
    def is_super(self, user: User) -> bool:
        return (
            user.is_staff or
            user.is_superuser or
            isinstance(user, GraderUser) # grader is considered admin
        )

    def has_object_permission(self, request: HttpRequest, view: Any, obj: UserProfile) -> bool:
        if not isinstance(obj, UserProfile):
            return True

        user = cast(User, request.user)
        return user and (
            (user.id is not None and user.id == obj.user_id) or
            self.is_super(user)
        )

    def filter_queryset(
            self,
            request: HttpRequest,
            queryset: QuerySet[UserProfile],
            view: Any,
            ) -> QuerySet[UserProfile]:
        user = cast(User, request.user)
        if issubclass(queryset.model, UserProfile) and not self.is_super(user):
            queryset = queryset.filter(user_id=user.id)
        return queryset


class IsTeacherOrAdminOrSelf(IsAdminOrUserObjIsSelf):
    def is_super(self, user: User) -> bool:
        if super().is_super(user):
            return True
        # FIXME: inefficient database query
        # Loop over every course instance in the database to check if the user
        # is a teacher on any course instance.
        every_course = CourseInstance.objects.all()
        return any(course.is_teacher(user) for course in every_course)


class GraderUserCanOnlyRead(Permission):
    def has_permission(self, request: HttpRequest, view: Any) -> bool:
        return (
            not isinstance(request.user, GraderUser) or
            request.method in SAFE_METHODS
        )


class IsLTIServiceUser(Permission):
    def has_permission(self, request: HttpRequest, view: Any) -> bool:
        return isinstance(request.user, LTIServiceUser)
