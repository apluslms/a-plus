from typing import Any, Dict, Optional, Set, Union

from django.db.models.aggregates import Count
from django.db.models.query import Prefetch, QuerySet
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_csv.renderers import CSVRenderer
from rest_framework_extensions.mixins import NestedViewSetMixin

from lib.api.renderers import CSVExcelRenderer
from lib.api.mixins import MeUserMixin
from lib.api.constants import REGEX_INT_ME
from course.api.mixins import CourseResourceMixin
from course.permissions import IsCourseAdminOrUserObjIsSelf
from userprofile.models import UserProfile

from ...cache.points import CachedPoints
from ...models import BaseExercise, Submission
from .submission_sheet import filter_best_submissions, submissions_sheet
from .aggregate_sheet import aggregate_sheet
from .aggregate_points import aggregate_points


class CourseSubmissionDataViewSet(NestedViewSetMixin,
                                  MeUserMixin,
                                  CourseResourceMixin,
                                  viewsets.ReadOnlyModelViewSet):
    """
    The `submissiondata` endpoint returns information in CSV format about the
    users' submissions in exercises in the course.

    Operations
    ----------

    `GET /courses/<course_id>/submissiondata/`:
        returns the submission data of all users as CSV.

    `GET /courses/<course_id>/submissiondata/<user_id>`:
        returns the submission data of a specific user as CSV.

    `GET /courses/<course_id>/submissiondata/me`:
        returns the submission data of the current user as CSV.

    All operations support the following URL parameters for filtering:

    - `filter`: the exercise number as a string, including module and chapter numbers
        (format N.N.N)
    - `category_id`: id of the exercise category
    - `module_id`: id of the course module
    - `exercise_id`: id of the exercise
    - `best`: "yes" or "no"; "no" includes all different submissions from same submitters
    - `field`: return submission data only for the given field, e.g., "field_0"
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
    )
    renderer_classes = [
        CSVRenderer,
        CSVExcelRenderer,
    ] + api_settings.DEFAULT_RENDERER_CLASSES
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {'course_id': 'enrollment.course_instance.id'}

    def get_queryset(self):
        if self.action == 'list':
            return self.instance.students
        return self.instance.course_staff_and_students

    def get_search_args(self, request):
        return {
            'number': request.GET.get('filter'),
            'category_id': int_or_none(request.GET.get('category_id')),
            'module_id': int_or_none(request.GET.get('module_id')),
            'exercise_id': int_or_none(request.GET.get('exercise_id')),
            'filter_for_assistant': not self.is_teacher,
            'best': request.GET.get('best') != 'no',
        }

    def list(
            self,
            request: Request,
            version: Optional[Union[int, str]] = None,
            course_id: Optional[Union[int, str]] = None,
            ) -> Response:
        profiles = self.filter_queryset(self.get_queryset())
        search_args = self.get_search_args(request)
        # Here, CachedPoints is only used to find the exercises whose feedback
        # is visible to the request user, and not the points for that user.
        # Therefore it is okay to use CachedPoints, even though this view
        # includes many users and CachedPoints includes only one.
        points = CachedPoints(self.instance, request.user, self.content, self.is_course_staff)
        ids = [e['id'] for e in self.content.search_exercises(**search_args)]
        revealed_ids = get_revealed_exercise_ids(search_args, points)
        queryset = Submission.objects.filter(
            exercise_id__in=ids,
            submitters__in=profiles
        ).prefetch_related(Prefetch('exercise', BaseExercise.objects.all()), 'notifications', 'files')
        return self.serialize_submissions(request, queryset, revealed_ids, best=search_args['best'])

    def retrieve(
            self,
            request: Request,
            version: Optional[Union[int, str]] = None,
            course_id: Optional[Union[int, str]] = None,
            user_id: Optional[Union[int, str]] = None,
            ) -> Response:
        profile = self.get_object()
        search_args = self.get_search_args(request)
        points = CachedPoints(self.instance, profile.user, self.content, self.is_course_staff)
        ids = points.submission_ids(**search_args)
        revealed_ids = get_revealed_exercise_ids(search_args, points)
        queryset = Submission.objects.filter(
            id__in=ids
        ).prefetch_related(Prefetch('exercise', BaseExercise.objects.all()), 'notifications', 'files')
        return self.serialize_submissions(request, queryset, revealed_ids)

    def serialize_submissions(
            self,
            request: Request,
            queryset: QuerySet[Submission],
            revealed_ids: Set[int],
            best: bool = False
            ) -> Response:
        submissions = list(queryset.order_by('exercise_id', 'id'))
        if best:
            submissions = filter_best_submissions(submissions, revealed_ids)

        # Pick out a single field.
        field = request.GET.get('field')
        if field:
            def submitted_field(submission, name):
                for key,val in (submission.submission_data or []):
                    if key == name:
                        return val
                return ""
            vals = [submitted_field(s, field) for s in submissions]
            return Response([v for v in vals if v != ""])

        data,fields = submissions_sheet(request, submissions, revealed_ids)
        self.renderer_fields = fields
        response = Response(data)
        if isinstance(getattr(request, 'accepted_renderer'), CSVRenderer):
            response['Content-Disposition'] = 'attachment; filename="submissions.csv"'
        return response

    def get_renderer_context(self):
        context = super().get_renderer_context()
        context['header'] = getattr(self, 'renderer_fields', None)
        return context


class CourseAggregateDataViewSet(NestedViewSetMixin,
                                 MeUserMixin,
                                 CourseResourceMixin,
                                 viewsets.ReadOnlyModelViewSet):
    """
    The `aggregatedata` endpoint returns aggregate information in CSV format
    about the users' submissions in exercises in the course.

    Operations
    ----------

    `GET /courses/<course_id>/aggregatedata/`:
        returns the aggregate submission data of all users as CSV.

    `GET /courses/<course_id>/aggregatedata/<user_id>`:
        returns the aggregate submission data of a specific user as CSV.

    `GET /courses/<course_id>/aggregatedata/me`:
        returns the aggregate submission data of the current user as CSV.

    All operations support the following URL parameters for filtering:

    - `filter`: the exercise number as a string, including module and chapter numbers
        (format N.N.N)
    - `category_id`: id of the exercise category
    - `module_id`: id of the course module
    - `exercise_id`: id of the exercise
    """
    # submission_count, total_points, max_points, (time_usage) / exercise / chapter / module
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
    )
    renderer_classes = [
        CSVRenderer,
    ] + api_settings.DEFAULT_RENDERER_CLASSES
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {'course_id': 'enrollment.course_instance.id'}

    def get_queryset(self):
        if self.action == 'list':
            return self.instance.students
        return self.instance.course_staff_and_students

    def get_search_args(self, request):
        return {
            'number': request.GET.get('filter'),
            'category_id': int_or_none(request.GET.get('category_id')),
            'module_id': int_or_none(request.GET.get('module_id')),
            'exercise_id': int_or_none(request.GET.get('exercise_id')),
            'filter_for_assistant': not self.is_teacher,
        }

    def list(self, request, version=None, course_id=None):
        profiles = self.filter_queryset(self.get_queryset())
        return self.serialize_profiles(request, profiles)

    def retrieve(self, request, version=None, course_id=None, user_id=None):
        return self.serialize_profiles(request, [self.get_object()])

    def serialize_profiles(self, request: Request, profiles: QuerySet[UserProfile]) -> Response:
        search_args = self.get_search_args(request)
        entry, exercises = self.content.search_entries(**search_args)
        ids = [e['id'] for e in exercises if e['type'] == 'exercise']
        points = CachedPoints(self.instance, request.user, self.content, self.is_course_staff)
        revealed_ids = get_revealed_exercise_ids(search_args, points)
        aggr = (
            Submission.objects
            .filter(exercise__in=ids, submitters__in=profiles)
            .exclude(status__in=(
                Submission.STATUS.UNOFFICIAL, Submission.STATUS.ERROR, Submission.STATUS.REJECTED,
            ))
            .values('submitters__user_id', 'exercise_id')
            .annotate(count=Count('id'))
            .annotate_submitter_points('total', revealed_ids)
            .order_by()
        )
        data,fields = aggregate_sheet(
            profiles,
            self.instance.taggings.all(),
            exercises,
            aggr,
            entry['number'] if entry else "",
        )
        self.renderer_fields = fields
        response = Response(data)
        if isinstance(getattr(request, 'accepted_renderer'), CSVRenderer):
            response['Content-Disposition'] = 'attachment; filename="aggregate.csv"'
        return response

    def get_renderer_context(self):
        context = super().get_renderer_context()
        context['header'] = getattr(self, 'renderer_fields', None)
        return context


class CourseResultsDataViewSet(NestedViewSetMixin,
                               CourseResourceMixin,
                               viewsets.ReadOnlyModelViewSet):
    """
    The `resultsdata` endpoint returns the students' points in the course
    in CSV format.

    Operations
    ----------

    `GET /courses/<course_id>/resultsdata/`:
        returns the points of all users as CSV.

    `GET /courses/<course_id>/resultsdata/<user_id>`:
        returns the points of a specific user as CSV.

    All operations support the following URL parameters for filtering:

    - `filter`: the exercise number as a string, including module and chapter numbers
        (format N.N.N)
    - `category_id`: id of the exercise category
    - `module_id`: id of the course module
    - `exercise_id`: id of the exercise
    - `show_unofficial`: if "true", unofficial submissions are included in the results
    """
    # submission_count, total_points, max_points, (time_usage) / exercise / chapter / module
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
    )
    renderer_classes = [
        CSVRenderer,
    ] + api_settings.DEFAULT_RENDERER_CLASSES
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {'course_id': 'enrollment.course_instance.id'}

    def get_queryset(self):
        if self.action == 'list':
            return self.instance.students
        return self.instance.course_staff_and_students

    def get_search_args(self, request):
        return {
            'number': request.GET.get('filter'),
            'category_id': int_or_none(request.GET.get('category_id')),
            'module_id': int_or_none(request.GET.get('module_id')),
            'exercise_id': int_or_none(request.GET.get('exercise_id')),
            'filter_for_assistant': not self.is_teacher,
       }

    def list(self, request, version=None, course_id=None):
        profiles = self.filter_queryset(self.get_queryset())
        return self.serialize_profiles(request, profiles)

    def retrieve(self, request, version=None, course_id=None, user_id=None):
        return self.serialize_profiles(request, [self.get_object()])

    def serialize_profiles(self, request: Request, profiles: QuerySet[UserProfile]) -> Response:
        search_args = self.get_search_args(request)
        _, exercises = self.content.search_entries(**search_args)
        ids = [e['id'] for e in exercises if e['type'] == 'exercise']
        points = CachedPoints(self.instance, request.user, self.content, self.is_course_staff)
        revealed_ids = get_revealed_exercise_ids(search_args, points)
        exclude_list = [Submission.STATUS.ERROR, Submission.STATUS.REJECTED]
        show_unofficial = request.GET.get('show_unofficial') == 'true'
        if not show_unofficial:
            exclude_list.append(Submission.STATUS.UNOFFICIAL)
        aggr = (
            Submission.objects
            .filter(exercise__in=ids, submitters__in=profiles)
            .exclude(status__in=(exclude_list))
            .values('submitters__user_id', 'exercise_id')
            .annotate(count=Count('id'))
            .annotate_submitter_points('total', revealed_ids, show_unofficial)
            .order_by()
        )
        data,fields = aggregate_points(
            profiles,
            self.instance.taggings.all(),
            exercises,
            aggr,
        )
        self.renderer_fields = fields
        response = Response(data)
        if isinstance(getattr(request, 'accepted_renderer'), CSVRenderer):
            response['Content-Disposition'] = 'attachment; filename="aggregate.csv"'
        return response

    def get_renderer_context(self):
        context = super().get_renderer_context()
        context['header'] = getattr(self, 'renderer_fields', None)
        return context


def int_or_none(value):
    if not value is None:
        try:
            return int(value)
        except ValueError:
            pass
    return None


def get_revealed_exercise_ids(search_args: Dict[str, Any], points: CachedPoints) -> Set[int]:
    """
    Helper function that returns the IDs of the exercises whose feedback has
    been revealed.
    """
    _, exercises = points.search_entries(**search_args)
    return {
        e['id'] for e in exercises
        if e['type'] == 'exercise'
        and e['submittable']
        and e['feedback_revealed']
    }
