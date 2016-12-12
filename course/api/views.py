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

from exercise.api.full_serializers import SubmissionDataSerializer
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
        IsAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsAdminOrUserObjIsSelf,
    )
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {'course_id': 'enrolled.id'}
    serializer_class = UserBriefSerializer
    queryset = UserProfile.objects.all()


class CoursePointsViewSet(NestedViewSetMixin,
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
    parent_lookup_map = {'course_id': 'enrolled.id'}
    queryset = UserProfile.objects.all()

    def retrieve(self, request, course_id, version, user_id=None):
        profile = self.get_object()
        students_results = self.student_information(profile, course_id, request)
        points = CachedPoints(self.instance, profile.user, self.content)
        students_results = self.students_rounds(
            profile, points, students_results, request, course_id
        )
        return Response(students_results)

    def list(self, request, course_id, version):
        students_results = {}
        for student in self.filter_queryset(self.get_queryset()):
            students_results[student.id] = self.student_information(
                student, course_id, request
            )
        return Response(students_results)

    def _copy_obj_fields(self, data, fields):
        out = {}
        for key in fields:
            out[key] = data[key]
        return out

    def students_rounds(self, student, points, students_results, request, course_id):
        """
        Get students points in dict. Structure of dict is:
        round
            points got in this round
            points to pass this round
            exercises of this round
                exercise1
                ...
        """
        # FIXME better to list modules and exercise in order than map them
        weeks = {}
        for module in points.modules_flatted():
            module_json = self._copy_obj_fields(module, [
                'max_points', 'points_to_pass',
                'submission_count', 'points', 'points_by_difficulty', 'passed',
            ])

            # FIXME remove the strange key values kept here for backwards compatibility
            module_json["total points"] = module['points']
            module_json["points to pass"] = module['points_to_pass']

            exercises = {}
            for entry in module['flatted']:
                if entry['type'] == 'exercise' and entry['submittable']:
                    exercise_json = self._copy_obj_fields(entry, [
                        'max_points', 'points_to_pass', 'difficulty',
                        'submission_count', 'points', 'passed',
                    ])

                    # FIXME remove the strange key values kept here for backwards compatibility
                    exercise_json["got_points"] = entry['points']

                    exercises[entry['name']] = exercise_json
            module_json["exercises"] = exercises

            week_link = reverse('api:course-exercises-detail', kwargs={
                'version':2,
                'course_id': course_id,
                'exercisemodule_id': module['id'],
            }, request=request)
            weeks[week_link] = module_json

        students_results["rounds"] = weeks

        total = points.total()
        students_results['submission_count'] = total['submission_count']
        students_results['points'] = total['points']
        students_results['points_by_difficulty'] = total['points_by_difficulty']

        return students_results

    def student_information(self, student, course_id, request):
        student_detail = reverse('api:course-points-detail', kwargs={
            'version': 2, 'course_id': course_id, 'user_id': student.id,
        }, request=request)
        student_link = reverse('api:user-detail', kwargs={
            'version': 2, 'user_id': student.id,
        }, request=request)
        return {
            "studentnumber": student.student_id,
            "userprofile": student_link,
            "pointsdetails": student_detail,
        }


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

import sys
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
        IsAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsAdminOrUserObjIsSelf,
    )
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
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
