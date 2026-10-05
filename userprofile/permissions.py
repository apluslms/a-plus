from aplus_auth.payload import Permission as AccessPermission
from django.contrib.auth.models import User

from authorization.permissions import SAFE_METHODS, Permission, FilterBackend
from exercise.models import Submission
from course.models import CourseInstance

from .models import UserProfile, GraderUser, LTIServiceUser

class IsAdminOrUserObjIsSelf(Permission, FilterBackend):
    def is_super(self, user):
        # NOTE: GraderUser must NOT be treated as an admin here. It used to be
        # (a 2016 "temporary fix"), which allowed any valid grader token --
        # e.g. an exercise token visible in a grader page URL -- to read every
        # user profile in the system. Graders may only reach user profiles
        # that their token permissions actually grant, which is checked in
        # has_object_permission via is_grantee_of_grader.
        return (
            not isinstance(user, GraderUser) and (
                user.is_staff or
                user.is_superuser
            )
        )

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, UserProfile):
            return True

        user = request.user
        if not user:
            return False

        if user.id is not None and user.id == obj.user_id:
            return True
        if self.is_super(user):
            return True
        if isinstance(user, GraderUser):
            return self.is_grantee_of_grader(user, obj)
        return False

    @staticmethod
    def is_grantee_of_grader(user: GraderUser, profile: UserProfile) -> bool:
        """
        Check if the user profile is covered by a grader token's permissions,
        i.e. it is a submitter of a submission the token has READ access to,
        or the target user of a submission creation granted by the token.
        WRITE alone does not grant access to user profiles.
        """
        submission_ids = [
            submission.id
            for permission, submission in user.permissions.submissions.instances
            if permission == AccessPermission.READ
        ]
        if submission_ids and profile.submissions.filter(
                id__in=submission_ids).exists():
            return True
        for _, info in user.permissions.submissions.creates:
            # user_id may be a string when it comes from a signed token
            grader_user_id = info.get("user_id")
            if grader_user_id is not None and str(profile.user_id) == str(grader_user_id):
                return True
        return False

    def filter_queryset(self, request, queryset, view):
        user = request.user
        if issubclass(queryset.model, UserProfile):
            if isinstance(user, GraderUser):
                # Grader tokens are not tied to a single user id, so never
                # allow an unrestricted listing. Restrict to users that the
                # token's permissions grant, which in practice means the
                # email-search endpoint returns results only for those.
                return queryset.filter(
                    user_id__in=self._grader_granted_user_ids(user),
                )
            if not self.is_super(user):
                queryset = queryset.filter(user_id=user.id)
        return queryset

    @staticmethod
    def _grader_granted_user_ids(user: GraderUser):
        granted = set()
        submission_ids = [
            submission.id
            for permission, submission in user.permissions.submissions.instances
            if permission == AccessPermission.READ
        ]
        if submission_ids:
            granted.update(
                Submission.objects
                .filter(id__in=submission_ids)
                .values_list("submitters__user_id", flat=True)
            )
        for _, info in user.permissions.submissions.creates:
            # user_id is a string in tokens and may be empty for anonymous
            # exercise tokens
            user_id = info.get("user_id")
            if user_id in (None, ""):
                continue
            try:
                granted.add(int(user_id))
            except (TypeError, ValueError):
                pass
        return granted


class IsTeacherOrAdminOrSelf(IsAdminOrUserObjIsSelf):
    def is_super(self, user):
        if super().is_super(user):
            return True
        if isinstance(user, GraderUser):
            # A grader token's course WRITE permissions are checked by the
            # individual views/object permissions. There is no need (and it
            # would be an expensive full-table scan) to probe every course.
            return False
        if not (user and user.is_authenticated and isinstance(user, User)):
            return False
        # Check with a single query if the user is a teacher on any course
        # instance, instead of looping over every course in the database.
        return CourseInstance.objects.get_teaching(user.userprofile).exists()


class GraderUserCanOnlyRead(Permission):
    def has_permission(self, request, view):
        return (
            not isinstance(request.user, GraderUser) or
            request.method in SAFE_METHODS
        )


class IsLTIServiceUser(Permission):
    def has_permission(self, request, view):
        return isinstance(request.user, LTIServiceUser)
