from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wsgiref.util import FileWrapper
from rest_framework import mixins, permissions, viewsets
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.decorators import action
from rest_framework.settings import api_settings
from rest_framework_extensions.mixins import NestedViewSetMixin
from django.db import DatabaseError

from authorization.permissions import ACCESS
from lib.api.mixins import MeUserMixin, ListSerializerMixin
from lib.api.constants import REGEX_INT, REGEX_INT_ME
from userprofile.models import UserProfile, GraderUser
from userprofile.permissions import IsAdminOrUserObjIsSelf, GraderUserCanOnlyRead
from course.permissions import (
    IsCourseAdminOrUserObjIsSelf,
    OnlyCourseTeacherPermission,
)
from course.api.mixins import CourseResourceMixin
from course.api.serializers import StudentBriefSerializer
from exercise.async_views import _post_async_submission

from ..models import (
    Submission,
    SubmittedFile,
    BaseExercise,
    SubmissionManager,
    LearningObject,
)
from ..permissions import (
    SubmissionVisiblePermission,
    SubmissionVisibleFilter,
    SubmittedFileVisiblePermission,
)
from .mixins import (
    ExerciseResourceMixin,
    SubmissionResourceMixin,
)

from ..forms import (
    SubmissionCreateAndReviewForm,
)

from .serializers import *
from .full_serializers import *
from .custom_serializers import *


GRADER_PERMISSION = api_settings.DEFAULT_PERMISSION_CLASSES + [
    OnlyCourseTeacherPermission,
]
GRADER_PERMISSION = [p for p in GRADER_PERMISSION if p is not GraderUserCanOnlyRead]


class ExerciseViewSet(mixins.RetrieveModelMixin,
                      ExerciseResourceMixin,
                      viewsets.GenericViewSet):
    """
    The `exercises` endpoint returns information about a single exercise. This
    endpoint cannot be used for getting a list of all exercises. For that
    purpose, use `/courses/<course_id>/exercises/`.

    Operations
    ----------

    `GET /exercises/<exercise_id>/`:
        returns the details of a specific exercise.

    `POST /exercises/<exercise_id>/grader/`:
        used by automatic graders when grading a submission.
    """
    lookup_field = 'id'
    lookup_url_kwarg = 'exercise_id'
    lookup_value_regex = REGEX_INT
    serializer_class = ExerciseSerializer
    queryset = BaseExercise.objects.all()

    @action(
        detail=True,
        url_path='grader',
        url_name='grader',
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
        status, errors, students = exercise.check_submission_allowed(student)
        if status != exercise.SUBMIT_STATUS.ALLOWED:
            return Response({'success': False, 'errors': errors})
        submission = Submission.objects.create(exercise=exercise)
        submission.submitters.set(students)

        # grade and update submission with data
        return Response(_post_async_submission(request, exercise, submission, errors))


class ExerciseSubmissionsViewSet(NestedViewSetMixin,
                                 ExerciseResourceMixin,
                                 MeUserMixin,
                                 mixins.ListModelMixin,
                                 viewsets.GenericViewSet):
    """
    The `submissions` endpoint returns information about the submissions of an
    exercise. Can also be used for creating new submissions and submitting them
    for grading.

    Operations
    ----------

    `GET /exercises/<exercise_id>/submissions/`:
        returns a list of all submissions.

    `GET /exercises/<exercise_id>/submissions/<user_id>/`:
        returns a list of a specific user's submissions.

    `GET /exercises/<exercise_id>/submissions/me/`:
        returns a list of the current user's submissions.

    `POST /exercises/<exercise_id>/submissions/`:
        creates a new submission. Only for teachers.

    - Body data:
        - One of:
            - `students`
            - `students_by_user_id`
            - `students_by_student_id`
            - `students_by_email`
        - `feedback`
        - `assistant_feedback`
        - `grading_data`
        - `points`
        - `submission_time`

    `POST /exercises/<exercise_id>/submissions/submit/`:
        submits a new submission for grading. Students are allowed to use this
        endpoint. The body data is used as submission data and files may be
        uploaded too.

    - Body data:
        - `_aplus_group`: group id when submitting as a group
        - Remaining key-value pairs match questions and their answers.
    """
    filter_backends = (
        SubmissionVisibleFilter,
    )
    lookup_field = 'submitters.user_id' # submitters.user.user.id == userprofile.user.id
    lookup_url_kwarg = 'user_id'
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
            filter_kwargs = {lookup_field.replace('.', '__'): self.kwargs[lookup_url_kwarg]}
            queryset = queryset.filter(**filter_kwargs)
        return super(ExerciseSubmissionsViewSet, self).filter_queryset(queryset)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def create(self, request, exercise_id, version):

        # TODO:
        # this currently works *ONLY* using a teacher API key

        submitter = request.user.userprofile
        data = request.data

        try:
            exercise = BaseExercise.objects.get(id=exercise_id)
        except BaseExercise.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        allowed_to_submit_status, msg1, msg2 = exercise.check_submission_allowed(submitter)
        if allowed_to_submit_status != exercise.SUBMIT_STATUS.ALLOWED:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if not exercise.course_instance.is_teacher(request.user):
            return Response('Only a teacher can make submissions via this API',
                            status=status.HTTP_403_FORBIDDEN)

        data = request.data

        if "submission_time" not in data:
            data['submission_time'] = timezone.now()

        form = SubmissionCreateAndReviewForm(data, exercise=exercise)

        if not form.is_valid():
            return Response({'status': 'error', 'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

        else:

            # check that submitters in whose name the submission is made are enrolled
            if not exercise.course_module.course_instance.get_student_profiles() \
                           .filter(pk__in=[s.pk for s in form.cleaned_students]) \
                           .count() == len(form.cleaned_students):
               return HttpResponse('Submitters must be enrolled to the course.',
                                   status=status.HTTP_400_BAD_REQUEST)

            sub = Submission.objects.create(exercise=self.exercise)
            sub.submitters.set(form.cleaned_students)
            sub.feedback = form.cleaned_data.get("feedback")
            sub.assistant_feedback = form.cleaned_data.get("assistant_feedback")
            sub.grading_data = form.cleaned_data.get("grading_data")
            sub.set_points(form.cleaned_data.get("points"),
                           self.exercise.max_points, no_penalties=True)
            sub.submission_time = form.cleaned_data.get("submission_time")
            sub.grader = submitter
            sub.grading_time = timezone.now()
            sub.set_ready()
            sub.save()

            return Response(status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        url_path='submit',
        url_name='submit',
        methods=['post'],
    )
    def submit(self, request, *args, **kwargs):
        # Stop submit trials for e.g. chapters.
        # However, allow posts from exercises switched to maintenance status.
        if not self.exercise.is_submittable:
            return self.http_method_not_allowed(request, *args, **kwargs)

        data = None
        status_code = None
        headers = None
        submission_status, issues, students = (
            self.exercise.check_submission_allowed(request.user.userprofile, request)
        )
        if submission_status == self.exercise.SUBMIT_STATUS.ALLOWED:
            try:
                new_submission = Submission.objects.create_from_post(
                    self.exercise, students, request)
            except ValueError as error:
                data = {
                    'detail': str(error),
                }
                status_code = status.HTTP_400_BAD_REQUEST
            except DatabaseError:
                data = {
                    'detail': _('ERROR_SUBMISSION_SAVING_FAILED'),
                }
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            else:
                page = self.exercise.grade(request, new_submission)

                # Enroll after succesfully submitting to the enrollment exercise.
                if self.exercise.status in (
                    LearningObject.STATUS.ENROLLMENT,
                    LearningObject.STATUS.ENROLLMENT_EXTERNAL,
                ) and new_submission.status == Submission.STATUS.READY:
                    self.instance.enroll_student(request.user)

                status_code = status.HTTP_201_CREATED
                headers = {
                    'Location': reverse('api:submission-detail', kwargs={
                                        'submission_id': new_submission.id,
                                        }, request=request),
                }
                if page.errors:
                    data = {'errors': page.errors}
        else:
            data = {'errors': issues}
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(data, status=status_code, headers=headers)

    def get_access_mode(self):
        # The API is not supposed to use the access mode permission in views,
        # but this is currently required so that enrollment exercises work in
        # the CourseVisiblePermission.
        access_mode = ACCESS.STUDENT

        # Loosen the access mode if this is an enrollment exercise.
        if self.exercise.status in (
                LearningObject.STATUS.ENROLLMENT,
                LearningObject.STATUS.ENROLLMENT_EXTERNAL,
              ):
            access_mode = ACCESS.ENROLL

        return access_mode


class ExerciseSubmitterStatsViewSet(ListSerializerMixin,
                                    NestedViewSetMixin,
                                    MeUserMixin,
                                    ExerciseResourceMixin,
                                    viewsets.ReadOnlyModelViewSet):
    """
    The `submitter_stats` endpoint returns statistical information about the
    students' submissions in this exercise, including current grade and
    submission count.

    Operations
    ----------

    `GET /exercises/<exercise_id>/submitter_stats/`:
        returns a list of all users.

    `GET /exercises/<exercise_id>/submitter_stats/<user_id>/`:
        returns a specific user's submission statistics.

    `GET /exercises/<exercise_id>/submitter_stats/me/`:
        returns the current user's submission statistics.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
    )
    lookup_field = 'user_id' # UserProfile.user.id
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    # Following produces duplicate profiles for each submission
    #parent_lookup_map = {'exercise_id': 'submissions.exercise.id'}
    listserializer_class = SubmitterStatsBriefSerializer
    serializer_class = SubmitterStatsSerializer
    queryset = UserProfile.objects.all()


class SubmissionViewSet(mixins.RetrieveModelMixin,
                        SubmissionResourceMixin,
                        viewsets.GenericViewSet):
    """
    The `submissions` endpoint returns information about a single submissions
    in an exercise. This endpoint cannot be used for listing all submissions.
    To view a list of all submissions in an exercise, use
    `/exercises/<exercise_id>/submissions/`.

    Operations
    ----------

    `GET /submissions/<submission_id>/`:
        returns the details of a specific submission.

    `GET /submissions/<submission_id>/grader/`:
        used by automatic graders when grading a submission.
    """
    lookup_field = 'id'
    lookup_url_kwarg = 'submission_id'
    lookup_value_regex = REGEX_INT
    serializer_class = SubmissionSerializer
    queryset = Submission.objects.all()

    @action(
        detail=True,
        url_path='grader',
        url_name='grader',
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


class SubmissionFileViewSet(NestedViewSetMixin,
                            SubmissionResourceMixin,
                            viewsets.ReadOnlyModelViewSet):
    """
    The `files` endpoint is used for downloading files sent as attachments of a
    submission.

    Operations
    ----------

    `GET /submissions/<submission_id>/files/<submittedfile_id>`:
        returns the details of a specific file.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        SubmittedFileVisiblePermission,
    ]
    lookup_url_kwarg = 'submittedfile_id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {
        'submission_id': 'submission.id',
    }
    queryset = SubmittedFile.objects.all()

    def list(self, request, version=None, submission_id=None):
        return Response([])

    def retrieve(self, request, version=None, submission_id=None, submittedfile_id=None):
        sfile = self.get_object()
        try:
            f = sfile.file_object.open()
        except OSError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(FileWrapper(f), content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(sfile.filename)
        return response


class CoursePointsViewSet(ListSerializerMixin,
                          NestedViewSetMixin,
                          MeUserMixin,
                          CourseResourceMixin,
                          viewsets.ReadOnlyModelViewSet):
    """
    The `points` endpoint returns information about the points earned in the
    course by the user.

    Operations
    ----------

    `GET /courses/<course_id>/points/`:
        returns a list of all users.

    `GET /courses/<course_id>/points/<user_id>/`:
        returns a list of a specific user's points.

    `GET /courses/<course_id>/points/me/`:
        returns a list of the current user's points.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
    )
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {}
    listserializer_class = StudentBriefSerializer
    serializer_class = UserPointsSerializer
    queryset = UserProfile.objects.all()
