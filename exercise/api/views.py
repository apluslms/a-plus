from io import BytesIO
import zipfile

from aplus_auth.payload import Permission
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponse, FileResponse
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wsgiref.util import FileWrapper
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.decorators import action
from rest_framework.settings import api_settings
from rest_framework_extensions.mixins import NestedViewSetMixin
from django.db import DatabaseError
from django.db.models import QuerySet

from authorization.permissions import ACCESS
from lib.api.mixins import MeUserMixin, ListSerializerMixin
from lib.api.constants import REGEX_INT, REGEX_INT_ME
from lib.api.statistics import BaseStatisticsView
from userprofile.models import UserProfile, GraderUser
from course.permissions import (
    IsCourseAdminOrUserObjIsSelf,
    JWTSubmissionCreatePermission,
    JWTSubmissionWritePermission,
    OnlyCourseStaffPermission,
)
from course.api.mixins import CourseResourceMixin
from course.models import SubmissionTag
from exercise.submission_models import SubmissionTagging
from exercise.async_views import _post_async_submission

from ..cache.points import ExercisePoints
from ..models import (
    Submission,
    SubmittedFile,
    SubmissionTag,
    BaseExercise,
    LearningObject,
)
from ..permissions import (
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
from .serializers import SubmissionBriefSerializer, SubmitterStatsBriefSerializer
from .full_serializers import (
    ExerciseSerializer,
    ExerciseGraderSerializer,
    ExerciseStatisticsSerializer,
    SubmissionSerializer,
    SubmissionGraderSerializer,
)
from .custom_serializers import SubmitterStatsSerializer, UserPointsSerializer


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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'cached_content': self.content})
        return context

    @action(
        detail=True,
        url_path='grader',
        url_name='grader',
        methods=['get', 'post'],
        get_permissions = lambda: [JWTSubmissionCreatePermission()],
        serializer_class = ExerciseGraderSerializer,
    )
    def grader_detail(self, request, *args, **kwargs):
        # Retrieve grading info
        if request.method in permissions.SAFE_METHODS:
            return self.retrieve(request, *args, **kwargs)

        ## submit and grade new submission

        # Onyl grader is allowed to post to this resource
        user = request.user
        if not isinstance(user, GraderUser):
            raise PermissionDenied(
                "Posting to grading url is only allowed with grader "
                "authentication token"
            )

        info = user.permissions.submissions.get_create(exercise=self.exercise)[1]
        if info is None:
            raise PermissionDenied(
                "You are allowed only to create new submission to exercise "
                "that your grader atuhentication token is for."
            )

        # resolve submiting user from grader token
        user_id = info.get("user_id")
        if not user_id and user_id != 0:
            raise PermissionDenied(
                "There is no user_id stored in your grader authentication token, "
                "so it can't be used to create new submission."
            )
        try:
            student = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            raise PermissionDenied( # pylint: disable=raise-missing-from
                "User_id in your grader authentication token doesn't really exist, "
                "so you can't create new submission with your grader token."
            )

        # find out if student can submit new exercise and if ok create submission template
        status, alerts, students = self.exercise.check_submission_allowed(student)
        errors = alerts['error_messages'] + alerts['warning_messages']

        if status != self.exercise.SUBMIT_STATUS.ALLOWED:
            return Response({'success': False, 'errors': errors})
        submission = Submission.objects.create(exercise=self.exercise)
        submission.submitters.set(students)

        # grade and update submission with data
        return Response(_post_async_submission(request, self.exercise, submission, errors))


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
        return super().filter_queryset(queryset)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def create(self, request, exercise_id, version): # pylint: disable=unused-argument

        # TODO:
        # this currently works *ONLY* using a teacher API key

        submitter = request.user.userprofile
        data = request.data

        try:
            exercise = BaseExercise.objects.get(id=exercise_id)
        except BaseExercise.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        allowed_to_submit_status, _msg1, _msg2 = exercise.check_submission_allowed(submitter)
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
        submission_status, alerts, students = (
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
                page = self.exercise.grade(new_submission, request)

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
            errors = alerts['error_messages'] + alerts['warning_messages'] + alerts['info_messages']
            data = {'errors': errors}
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(data, status=status_code, headers=headers)

    @action(
        detail=False,
        url_path='zip',
        url_name='zip',
        methods=['get'],
    )
    def zip(self, request, exercise_id, *args, **kwargs): # pylint: disable=too-many-locals # noqa: MC0001
        if not self.instance.is_course_staff(request.user):
            return Response(
                'Only course staff can download submissions via this API',
                status=status.HTTP_403_FORBIDDEN,
        )
        exercise = None
        try:
            exercise = BaseExercise.objects.get(id=exercise_id)
        except BaseExercise.DoesNotExist:
            return Response('Exercise not found', status=status.HTTP_404_NOT_FOUND)

        best = request.query_params.get('best') == 'yes'
        submissions = Submission.objects.filter(exercise__id=exercise_id).order_by('submission_time')

        def get_group_id(submission):
            group_id = None
            if 'group' in submission.meta_data:
                group_id = submission.meta_data['group']
            if group_id is None:
                for lst in submission.submission_data:
                    if '_aplus_group' in lst:
                        group_id = lst[1]
                        break
            return group_id

        # pylint: disable-next=too-many-locals
        def handle_submission(submission, submitters, info_csv):
            group_id = None
            if len(submitters) > 1:
                group_id = get_group_id(submission)
                if group_id is not None:
                    try:
                        group_id = int(group_id)
                    except ValueError:
                        return info_csv
            submission_time = submission.submission_time.strftime('%Y-%m-%d %H:%M:%S %z')
            points = submission.service_points
            submission_id = submission.id
            submitter_name = ";".join([submitter.user.get_full_name() for submitter in submission.submitters.all()])
            exercise_form_name = ";".join(list(submission.exercise.exercise_info["form_i18n"].keys()))
            submitted_files = SubmittedFile.objects.filter(submission=submission)
            student_ids = sorted([str(submitter.student_id) for submitter in submitters])
            submitters_string = '+'.join(student_ids)
            submission_num = list(
                dict.fromkeys( # Remove duplicates
                    Submission.objects.filter(exercise__id=exercise_id, submitters__in=submitters)
                    .order_by('submission_time')
                )
            ).index(submission) + 1
            for i, submitted_file in enumerate(submitted_files, start=1):
                filename = f"{submitters_string}_file{i}_submission{submission_num}"
                original_name = submitted_file.filename
                try:
                    with submitted_file.file_object.file.open('rb') as file:
                        zip_file.writestr(f'{filename}', file.read())
                    if group_id is not None:
                        info_csv += (
                            f"{filename},group{group_id},{submission_time},{original_name},{points},"
                            f"{submission_id},{submitter_name},{exercise_form_name},{submission_num}\n"
                        )
                    else:
                        info_csv += (
                            f"{filename},{submitters_string},{submission_time},{original_name},{points},"
                            f"{submission_id},{submitter_name},{exercise_form_name},{submission_num}\n"
                        )
                except OSError:
                    pass
            return info_csv

        # Create a zip file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            info_csv = (
                "filename,label,created_at,original_name,points,submission_id,"
                "submitter_name,exercise_form_name,submission_index\n"
            )
            if best:
                unique_submitters = []
                for submission in submissions:
                    submitters = submission.submitters.all()
                    if any(self.instance.is_course_staff(submitter.user) for submitter in submitters):
                        # Skip staff submissions
                        continue
                    for submitter in submitters:
                        if submitter not in unique_submitters:
                            unique_submitters.append(submitter)
                unique_submissions = []
                for submitter in unique_submitters:
                    submission_entry = ExercisePoints.get(exercise, submitter.user).best_submission
                    if submission_entry is None:
                        continue
                    submission = submissions.filter(id=submission_entry.id).first()
                    # Prevent duplicate best submissions due to group submissions
                    if submission not in unique_submissions:
                        unique_submissions.append(submission)
                        info_csv = handle_submission(submission, submission.submitters.all(), info_csv)
            else:
                for submission in submissions:
                    submitters = submission.submitters.all()
                    if any(self.instance.is_course_staff(submitter.user) for submitter in submitters):
                        # Skip staff submissions
                        continue
                    info_csv = handle_submission(submission, submitters, info_csv)
            zip_file.writestr('info.csv', info_csv)
        zip_buffer.seek(0)

        response = FileResponse(zip_buffer, as_attachment=True, filename='submissions.zip')
        return response

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

    def get_queryset(self):
        if self.action == 'list':
            return self.instance.students
        return self.instance.course_staff_and_students


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

    `GET /submissions/<submission_id>/re-submit/`:
        resubmits a submission for grading.

    `POST /submissions/<submission_id>/tag/`:
        tags a submission with a submission tag.

    - Request body:
        - `tag_slug`: the slug of the tag to be added.

    `DELETE /submissions/<submission_id>/tag/`:
        removes a submission tag from a submission.

    - Request body:
        - `tag_slug`: the slug of the tag to be removed.
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
        get_permissions = lambda: [JWTSubmissionWritePermission()],
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

        if user.permissions.submissions.has(Permission.WRITE, self.submission):
            raise PermissionDenied(
                "You are not allowed to grade other submissions than what "
                "your grader authentication token is for"
            )

        return Response(_post_async_submission(request, self.submission.exercise, self.submission))

    @action(
        detail=True,
        url_path='re-submit',
        url_name='re-submit',
        get_permissions = lambda: [OnlyCourseStaffPermission()],
        methods=['post'],
    )
    def resubmit(self, request, *args, **kwargs):
        if not self.submission.exercise.is_submittable:
            return self.http_method_not_allowed(request, *args, **kwargs)

        data = None

        page = self.submission.exercise.grade(self.submission, request)

        # Enroll after succesfully resubmitting to the enrollment exercise.
        if (self.submission.exercise.status in (
                    LearningObject.STATUS.ENROLLMENT,
                    LearningObject.STATUS.ENROLLMENT_EXTERNAL,
                ) and self.submission.status == Submission.STATUS.READY
                and page.is_loaded and page.is_accepted
                ):
            submitter = self.submission.submitters.first().user
            if not (
                    self.instance.is_student(submitter)
                    or self.instance.is_course_staff(submitter)
                    or self.instance.is_banned(submitter)
                    ):
                self.instance.enroll_student(submitter)

        headers = {
            'Location': reverse(
                'api:submission-detail',
                kwargs={'submission_id': self.submission.id},
                request=request,
            ),
        }
        if page.errors:
            data = {'errors': page.errors}

        return Response(data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=True,
        url_path='tag',
        url_name='tag',
        get_permissions = lambda: [OnlyCourseStaffPermission()],
        methods=['post', 'delete'],
    )
    def manage_tag(self, request, *args, **kwargs):
        """
        Add or remove a tag from a submission.

        Request data should include 'tag_slug' parameter.
        """
        tag_slug = request.data.get('tag_slug')
        if not tag_slug:
            return Response({'detail': 'Missing tag_slug parameter'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Try to get the tag and validate it belongs to the course
            tag = SubmissionTag.objects.get(
                slug=tag_slug,
                course_instance=self.submission.exercise.course_module.course_instance,
            )
        except SubmissionTag.DoesNotExist:
            return Response(
                {'detail': 'Tag not found or not part of this course'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == 'POST':
            # Check if the tagging already exists
            if SubmissionTagging.objects.filter(submission=self.submission, tag=tag).exists():
                return Response(
                    {'detail': 'This submission is already tagged with this tag'},
                    status=status.HTTP_409_CONFLICT,
                )

            SubmissionTagging.objects.create(submission=self.submission, tag=tag)
            return Response({'detail': 'Tag added successfully'}, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            try:
                # Get the tagging object
                tagging = SubmissionTagging.objects.get(submission=self.submission, tag=tag)
                tagging.delete()
            except SubmissionTagging.DoesNotExist:
                return Response(
                    {'detail': 'This submission is not tagged with this tag'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        return Response({'detail': 'Tag removed successfully'}, status=status.HTTP_200_OK)


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

    def list(self, request, version=None, submission_id=None): # pylint: disable=arguments-differ unused-argument
        return Response([])
    # pylint: disable-next=arguments-differ unused-argument
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
    listserializer_class = UserPointsSerializer
    serializer_class = UserPointsSerializer

    def get_course_instance_object(self):
        try:
            return super().get_course_instance_object()
        except Http404 as exc:
            raise NotFound(detail="Course not found.") from exc

    def get_queryset(self):
        if self.action == 'list':
            return self.instance.students
        return self.instance.course_staff_and_students

    def retrieve(self, request, *args, **kwargs):
        if not self.instance.is_student(request.user) and not self.instance.is_course_staff(request.user):
            return Response({'detail': 'You are not enrolled in the course.'}, status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, *args, **kwargs)


class ExerciseStatisticsView(BaseStatisticsView):
    """
    Returns submission statistics for an exercise, over a given time window.

    Returns the following attributes:

    - `submission_count`: total number of submissions.
    - `submitters`: number of users submitting.

    Operations
    ----------

    `GET /exercises/<exercise_id>/statistics/`:
        returns the statistics for the given exercise.

    - URL parameters:
        - `endtime`: date and time in ISO 8601 format indicating the end point
          of time window we are interested in. Default: now.
        - `starttime`: date and time in ISO 8601 format indicating the start point
          of time window we are interested in. Default: one day before endtime
    """

    serializer_class = ExerciseStatisticsSerializer

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        exercise_id = self.kwargs['exercise_id']
        return queryset.filter(
            exercise=exercise_id,
        )

    def get_object(self):
        obj = super().get_object()
        obj.update({ 'exercise_id': self.kwargs['exercise_id'] })
        return obj
