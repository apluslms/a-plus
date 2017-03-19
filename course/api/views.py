from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework import status
from rest_framework.reverse import reverse

from lib.viewbase import BaseMixin
from lib.api.mixins import ListSerializerMixin, MeUserMixin
from lib.api.constants import REGEX_INT, REGEX_INT_ME
from userprofile.models import UserProfile
from userprofile.permissions import IsAdminOrUserObjIsSelf
from userprofile.api.serializers import UserBriefSerializer
from course.permissions import OnlyCourseTeacherPermission, IsCourseAdminOrUserObjIsSelf

from exercise.api.custom_serializers import UserPointsSerializer, SubmissionDataSerializer
from exercise.cache.points import CachedPoints
from exercise.models import BaseExercise, Submission
from exercise.exercise_summary import ResultTable

from ..models import (
    CourseInstance,
    CourseModule,
    UserTag,
    UserTagging,
)
from .mixins import (
    CourseResourceMixin,
    CourseModuleResourceMixin,
)
from .serializers import *
from .full_serializers import *


class CourseViewSet(ListSerializerMixin,
                    CourseResourceMixin,
                    viewsets.ReadOnlyModelViewSet):
    lookup_url_kwarg = 'course_id'
    lookup_value_regex = REGEX_INT
    listserializer_class = CourseBriefSerializer
    serializer_class = CourseSerializer

    def get_queryset(self):
        return ( CourseInstance.objects
                 .get_visible(self.request.user)
                 .all() )

    def get_object(self):
        return self.get_member_object('instance', 'Course')


class CourseExercisesViewSet(NestedViewSetMixin,
                             CourseModuleResourceMixin,
                             CourseResourceMixin,
                             viewsets.ReadOnlyModelViewSet):
    lookup_url_kwarg = 'exercisemodule_id'
    lookup_value_regex = REGEX_INT
    parent_lookup_map = {'course_id': 'course_instance.id'}
    serializer_class = CourseModuleSerializer

    def get_queryset(self):
        return ( CourseModule.objects
                 .get_visible(self.request.user)
                 .all() )

    def get_object(self):
        return self.get_member_object('module', 'Exercise module')


class CourseStudentsViewSet(NestedViewSetMixin,
                            MeUserMixin,
                            CourseResourceMixin,
                            viewsets.ReadOnlyModelViewSet):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
    )
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    lookup_field = 'user__id'
    parent_lookup_map = {'course_id': 'enrolled.id'}
    serializer_class = UserBriefSerializer
    queryset = UserProfile.objects.all()


class CoursePointsViewSet(ListSerializerMixin,
                          NestedViewSetMixin,
                          MeUserMixin,
                          CourseResourceMixin,
                          viewsets.ReadOnlyModelViewSet):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
    )
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    lookup_field = 'user__id'
    parent_lookup_map = {'course_id': 'enrolled.id'}
    listserializer_class = CoursePointsBriefSerializer
    serializer_class = UserPointsSerializer
    queryset = UserProfile.objects.all()


class CourseUsertagsViewSet(NestedViewSetMixin,
                            CourseModuleResourceMixin,
                            CourseResourceMixin,
                            viewsets.ReadOnlyModelViewSet):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyCourseTeacherPermission,
    ]
    lookup_url_kwarg = 'usertag_id'
    serializer_class = CourseUsertagSerializer
    queryset = UserTag.objects.all()
    parent_lookup_map = {'course_id': 'course_instance_id'}


class CourseUsertaggingsViewSet(NestedViewSetMixin,
                                CourseModuleResourceMixin,
                                CourseResourceMixin,
                                viewsets.ReadOnlyModelViewSet):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyCourseTeacherPermission,
    ]
    lookup_url_kwarg = 'usertag_id'
    serializer_class = CourseUsertaggingsSerializer
    queryset = ( UserTagging.objects
                 .select_related('tag', 'user', 'user__user')
                 .only('tag__id', 'tag__course_instance',
                       'user__user__id', 'user__user__username', 'user__student_id',
                       'course_instance__id')
                 .all() )
    parent_lookup_map = {'course_id': 'course_instance_id'}

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        tag_id = self.request.GET.get('tag_id')
        if tag_id is not None:
            queryset = queryset.filter(tag__id=tag_id)
        return queryset


class CourseSubmissionDataViewSet(ListSerializerMixin,
                                  NestedViewSetMixin,
                                  MeUserMixin,
                                  CourseResourceMixin,
                                  viewsets.ReadOnlyModelViewSet):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
    )
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    lookup_field = 'user__id'
    parent_lookup_map = {'course_id': 'enrolled.id'}
    listserializer_class = CourseSubmissionsBriefSerializer
    serializer_class = SubmissionDataSerializer
    queryset = UserProfile.objects.all()

    def _int_or_none(self, value):
        if value is None:
            return None
        return int(value)

    def _submitted_field(self, submission, name):
        for key,val in submission.submission_data:
            if key == name:
                return val
        return ""

    def retrieve(self, request, course_id, version, user_id=None):
        profile = self.get_object()
        points = CachedPoints(self.instance, profile.user, self.content)
        ids = points.submission_ids(
            category_id=self._int_or_none(request.GET.get('category_id')),
            module_id=self._int_or_none(request.GET.get('module_id')),
            exercise_id=self._int_or_none(request.GET.get('exercise_id')),
            best=request.GET.get('best') != 'no',
        )
        submissions = Submission.objects.filter(id__in=ids)

        # Pick out a field.
        field = request.GET.get('field')
        if field:
            vals = [self._submitted_field(s, field) for s in submissions.all()]
            return Response([v for v in vals if v != ""])

        serializer = self.get_serializer(submissions, many=True)
        return Response(serializer.data)
