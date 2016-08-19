from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from rest_framework import mixins, permissions, viewsets
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.decorators import detail_route
from rest_framework.settings import api_settings
from rest_framework_extensions.mixins import NestedViewSetMixin

from lib.api.mixins import MeUserMixin, ListSerializerMixin
from lib.api.constants import REGEX_INT, REGEX_INT_ME
from userprofile.models import UserProfile, GraderUser
from userprofile.permissions import IsAdminOrUserObjIsSelf, GraderUserCanOnlyRead
from course.permissions import (
    IsCourseAdminOrUserItselfFilter,
    OnlyCourseTeacherPermission,
)
from exercise.async_views import _post_async_submission

from ..models import (
    Submission,
    BaseExercise,
    SubmissionManager,
)
from ..permissions import (
    SubmissionVisibleFilter,
)
from .mixins import (
    ExerciseResourceMixin,
    SubmissionResourceMixin,
)
from .serializers import *
from .full_serializers import *


GRADER_PERMISSION = api_settings.DEFAULT_PERMISSION_CLASSES + [
    OnlyCourseTeacherPermission,
]
GRADER_PERMISSION = [p for p in GRADER_PERMISSION if p is not GraderUserCanOnlyRead]


class ExerciseViewSet(mixins.RetrieveModelMixin,
                      ExerciseResourceMixin,
                      viewsets.GenericViewSet):
    """
    Url for GETting information about an exercise. (List of exercises can be
    fetched from /api/v2/courses/1/exercices)
    /api/v2/exercises/{exercise_id} (/api/v2/exercises/ does not actually exist)
    """
    lookup_url_kwarg = 'exercise_id'
    lookup_value_regex = REGEX_INT
    serializer_class = ExerciseSerializer
    queryset = BaseExercise.objects.all()

    @detail_route(
        url_path='grader',
        methods=['get', 'post'],
        permission_classes = GRADER_PERMISSION,
        serializer_class = ExerciseGraderSerializer,
    )
    def grader_detail(self, request, *args, **kwargs):
        # Retrieve grading info
        if request.method in permissions.SAFE_METHODS:
            return self.retrieve(request, *args, **kwargs)

        ## submit and grade new ssubmission

        # Onyl grader is allowed to post to this resource
        user = request.user
        if not isinstance(user, GraderUser):
            raise PermissionDenied(
                "Posting to grading url is only allowed with grader "
                "authentication token"
            )

        # compare exercise linked to grader token with exercise defined in url
        exercise = user._exercise
        if exercise != self.exercise:
            raise PermissionDenied(
                "You are allowed only to create new submission to exercise "
                "that your grader atuhentication token is for."
            )

        # resolve submiting user from grader token
        student_id = user._extra.get('student_id', None)
        if not student_id and student_id != 0:
            raise PermissionDenied(
                "There is no user_id stored in your grader authentication token, "
                "so it can't be used to create new submission."
            )
        try:
            student = UserProfile.objects.get(user_id=student_id)
        except UserProfile.DoesNotExist:
            raise PermissionDenied(
                "User_id in your grader authentication token doesn't really exist, "
                "so you can't create new submission with your grader token."
            )

        # make sure this was not submission token (after above check this should ever trigger)
        if user._submission is not None:
            raise PermissionDenied(
                "This grader authentication token is for specific submission, "
                "thus you can't create new submission with it."
            )

        # find out if student can submit new exercise and if ok create submission template
        ok, errors, students = exercise.is_submission_allowed(student)
        if not ok:
            return Response({'success': False, 'errors': errors})
        submission = Submission.objects.create(exercise=exercise)
        submission.submitters = students

        # grade and update submission with data
        return Response(_post_async_submission(request, exercise, submission, errors))


class ExerciseSubmissionsViewSet(NestedViewSetMixin,
                                 ExerciseResourceMixin,
                                 MeUserMixin,
                                 mixins.ListModelMixin,
                                 viewsets.GenericViewSet):
    """
    * /api/v2/exercises/{exercise_id}/submissions
    * POST: Make a submission. Returns brief information about submission
    (including link to submission resource: /api/v2/exercises/{exercise_id}/
    submissions/{submissions_id})
    * GET: User can also get his old submission with GET.
    """
    filter_backends = (
        SubmissionVisibleFilter,
        IsAdminOrUserObjIsSelf,
    )
    lookup_url_kwarg = 'user_id'
    lookup_field = 'submitters__user__id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {
        'exercise_id': 'exercise.id',
    }
    serializer_class = SubmissionBriefSerializer
    queryset = Submission.objects.all()

    def filter_queryset(self, queryset):
        lookup_field = self.lookup_field
        lookup_url_kwarg = self.lookup_url_kwarg or lookup_field
        if lookup_url_kwarg in self.kwargs:
            filter_kwargs = {lookup_field: self.kwargs[lookup_url_kwarg]}
            queryset = queryset.filter(**filter_kwargs)
        return super(ExerciseSubmissionsViewSet, self).filter_queryset(queryset)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    # For POSTing a submission. An extra parameter exercise_id comes
    # from url. UNDER CONSTRUCTION!
    def create(self, request, exercise_id, version):
        # SubmissionManager.create_from_post(exercise, request.user, request)
        # Kts. myös a-plus/exercise/views.py rivi 99
        # First parse the request
        submitter = request.user.userprofile
        data = request.data
        print(data)
        print(exercise_id)
        print(submitter)

        # Before submission we need to check if user is able to make a submission
        try:
            exercice_to_submit = BaseExercise.objects.get(id=exercise_id)
        except BaseExercise.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        print(exercice_to_submit)

        if exercice_to_submit.is_submission_allowed([submitter]):
            print("Submission is available.")

            #serializer = SubmissionSerializer(data=request.data)
            #if serializer.is_valid():
            #    serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class ExerciseSubmitterStatsViewSet(NestedViewSetMixin,
                                    ExerciseResourceMixin,
                                    ListSerializerMixin,
                                    MeUserMixin,
                                    mixins.ListModelMixin,
                                    viewsets.GenericViewSet):
    """
    Viewset contains info about exercise stats per user
    this includes current grade and submission count
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserItselfFilter,
    )
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {
        'exercise_id': 'submissions.exercise.id',
    }
    listserializer_class = UserListFieldWithStatsLink
    serializer_class = SubmitterStatsSerializer
    queryset = UserProfile.objects.all()

    def get_serializer(self, queryset, **kwargs):
        if self.action == 'list':
            queryset = {
                'submitters': queryset,
                'exercise_id': self.kwargs['exercise_id'],
            }
            kwargs['source'] = 'submitters'
        return super(ExerciseSubmitterStatsViewSet, self).get_serializer(queryset, **kwargs)

    def retrieve(self, request, exercise_id, user_id, **kwargs):
        # NOTE: user id's that do not exist in DB will raise 404 instead of permission denied
        user = ( request.user.userprofile
                 if user_id == request.user.id
                 else get_object_or_404(UserProfile, user_id=user_id) )
        self.check_object_permissions(request, user)
        submissions = ( Submission.objects.all()
            .filter(exercise_id=exercise_id, submitters=user)
            .order_by('-grade', '-submission_time') )
        submission_count = submissions.count()
        best_submission = submissions[0] if submission_count > 0 else None
        data = {
            'exercise_id': exercise_id,
            'user': user,
            'submissions': submissions,
            'submission_count': submission_count, # FIXME: doesn't skip false
            'best_submission': best_submission,
            'grade': best_submission.grade if best_submission else None,
        }
        serializer = self.get_serializer(data)
        return Response(serializer.data)


class SubmissionViewSet(mixins.RetrieveModelMixin,
                        SubmissionResourceMixin,
                        viewsets.GenericViewSet):
    """
    Interface to exercise submission model.
    Listing all submissions is not allowed (as there is no point),
    but are linked from exercises tree (`/exercise/<id>/submissions/`).
    """
    lookup_url_kwarg = 'submission_id'
    lookup_value_regex = REGEX_INT
    serializer_class = SubmissionSerializer
    queryset = Submission.objects.all()

    @detail_route(
        url_path='grader',
        methods=['get', 'post'],
        permission_classes = GRADER_PERMISSION,
        serializer_class = SubmissionGraderSerializer,
    )
    def grader_detail(self, request, *args, **kwargs):
        # Retrieve grading info
        if request.method in permissions.SAFE_METHODS:
            return self.retrieve(request, *args, **kwargs)

        ## submit grade info

        # get user and related exercise and submission
        user = request.user
        if not isinstance(user, GraderUser):
            raise PermissionDenied(
                "Posting to grading url is only allowed with grader "
                "authentication token"
            )

        exercise = user._exercise
        submission = user._submission

        # compare submission linked to grader token to submission in url
        if submission != self.submission:
            raise PermissionDenied(
                "You are not allowed to grade other submissions than what "
                "your grader authentication token is for"
            )

        return Response(_post_async_submission(request, exercise, submission))
