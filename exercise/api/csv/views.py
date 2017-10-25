from rest_framework import mixins, permissions, viewsets
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_csv.renderers import CSVRenderer
from rest_framework_extensions.mixins import NestedViewSetMixin

from lib.api.mixins import MeUserMixin, ListSerializerMixin
from lib.api.constants import REGEX_INT, REGEX_INT_ME
from course.api.mixins import CourseResourceMixin
from course.cache.students import CachedStudents
from course.permissions import IsCourseAdminOrUserObjIsSelf
from userprofile.models import UserProfile

from ...cache.points import CachedPoints
from ...models import (
    Submission,
)
from .submission_sheet import *
from .aggregate_sheet import *


class CourseSubmissionDataViewSet(ListSerializerMixin,
                                  NestedViewSetMixin,
                                  MeUserMixin,
                                  CourseResourceMixin,
                                  viewsets.ReadOnlyModelViewSet):
    """
    Lists submissions as data sheet.
    Following GET parameters may be used to filter submissions:
    category_id, module_id, exercise_id,
    best ("no" includes all different submissions from same submitters),
    field (a name of submitted value field to generate a simple value list)
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    renderer_classes = [
        CSVRenderer,
    ] + api_settings.DEFAULT_RENDERER_CLASSES
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    lookup_field = 'user__id'
    parent_lookup_map = {'course_id': 'enrolled.id'}
    queryset = UserProfile.objects.all()

    def get_search_args(self, request):
        def int_or_none(value):
            if value is None:
                return None
            return int(value)
        return {
            'category_id': int_or_none(request.GET.get('category_id')),
            'module_id': int_or_none(request.GET.get('module_id')),
            'exercise_id': int_or_none(request.GET.get('exercise_id')),
            'filter_for_assistant': not self.is_teacher,
            'best': request.GET.get('best') != 'no',
        }

    def list(self, request, version=None, course_id=None):
        search_args = self.get_search_args(request)
        ids = [e['id'] for e in self.content.search_exercises(**search_args)]
        queryset = Submission.objects.filter(exercise_id__in=ids)
        return self.serialize_submissions(request, queryset, best=search_args['best'])

    def retrieve(self, request, version=None, course_id=None, user_id=None):
        profile = self.get_object()
        points = CachedPoints(self.instance, profile.user, self.content)
        ids = points.submission_ids(**self.get_search_args(request))
        queryset = Submission.objects.filter(id__in=ids)
        return self.serialize_submissions(request, queryset)

    def serialize_submissions(self, request, queryset, best=False):
        submissions = list(queryset.order_by('exercise_id', 'id'))
        if best:
            submissions = filter_best_submissions(submissions)

        # Pick out a single field.
        field = request.GET.get('field')
        if field:
            def submitted_field(submission, name):
                for key,val in submission.submission_data:
                    if key == name:
                        return val
                return ""
            vals = [submitted_field(s, field) for s in submissions]
            return Response([v for v in vals if v != ""])

        data,fields = submissions_sheet(request, submissions)
        self.renderer_fields = fields
        response = Response(data)
        if isinstance(getattr(request, 'accepted_renderer'), CSVRenderer):
            response['Content-Disposition'] = 'attachment; filename="submissions.csv"'
        return response

    def get_renderer_context(self):
        context = super().get_renderer_context()
        context['header'] = getattr(self, 'renderer_fields', None)
        return context


class CourseAggregateDataViewSet(ListSerializerMixin,
                                 NestedViewSetMixin,
                                 MeUserMixin,
                                 CourseResourceMixin,
                                 viewsets.ReadOnlyModelViewSet):
    """
    List aggregate submission data as data sheet.
    """
    # submission_count, total_points, max_points, (time_usage) / exercise / chapter / module
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    renderer_classes = [
        CSVRenderer,
    ] + api_settings.DEFAULT_RENDERER_CLASSES
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    lookup_field = 'user__id'
    parent_lookup_map = {'course_id': 'enrolled.id'}
    queryset = UserProfile.objects.all()

    def list(self, request, version=None, course_id=None):
        return self.serialize_profiles(request, self.get_queryset())

    def retrieve(self, request, version=None, course_id=None, user_id=None):
        return self.serialize_profiles(request, [self.get_object()])

    def serialize_profiles(self, request, profiles):
        data,fields = aggregate_sheet(request, self.instance, self.content, profiles)
        self.renderer_fields = fields
        response = Response(data)
        if isinstance(getattr(request, 'accepted_renderer'), CSVRenderer):
            response['Content-Disposition'] = 'attachment; filename="aggregate.csv"'
        return response

    def get_renderer_context(self):
        context = super().get_renderer_context()
        context['header'] = getattr(self, 'renderer_fields', None)
        return context
