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
from course.permissions import OnlyCourseTeacherPermission

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
                          CourseResourceMixin,
                          viewsets.ReadOnlyModelViewSet):
    # Allow only staff to see points listings
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyCourseTeacherPermission,
    ]

    def retrieve(self, request, course_id, version, pk=None):
        """
        For getting students points in all exercises of the course.
        Also there's included points to pass value in course module
        and total of gathered points in that module
        """
        course_instance = CourseInstance.objects.get(id=course_id)
        table = ResultTable(course_instance)
        try:
            student_id = int(pk)
        except ValueError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if student_id not in table.results:
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            # Get selected student and his points sorted by weeks
            student = [x for x in table.students if x.id == student_id][0]
            students_results = self.student_information(student, course_id, request)
            students_results = self.students_rounds(student, table,
                                    students_results, request, course_id)

            return Response(students_results)


    def list(self, request, course_id, version):
        """
        For listing this courses students and links to their points
        """
        course_instance = CourseInstance.objects.get(id=course_id)
        table = ResultTable(course_instance)

        students_results = {}
        # Parse results for JSON-format.
        for student in table.students:
            students_results[student.id] = self.student_information(student,
                                                course_id, request)

        return Response(students_results)


    def students_rounds(self, student, table, students_results, request,
                        course_id):
        """
        Get students points in dict. Structure of dict is:
        round
            points got in this round
            points to pass this round
            exercises of this round
                exercise1
                ...
        """

        weeks = {}
        for exercise in table.exercises:
            got_points = table.results[student.id][exercise.id]
            if got_points is None:
                got_points = 0
            max_points = exercise.max_points

            week_link = reverse('api:course-exercises-detail', kwargs=
                                {
                                    'version':2,
                                    'course_id': course_id,
                                    'exercisemodule_id': exercise.course_module.id
                                },
                                 request=request)

            if week_link in weeks:
                weeks[week_link]["exercises"][exercise.name] = \
                                                {
                                                "got_points": got_points,
                                                "max_points": max_points
                                                }
                weeks[week_link]["total points"] += got_points
            else:
                weeks[week_link] = {
                    "total points": got_points,
                    "points to pass": exercise.course_module.points_to_pass,
                    "exercises": {
                        exercise.name: {
                            "got_points": got_points,
                            "max_points": max_points
                        }
                    }
                }

        students_results["rounds"] = weeks
        return students_results


    def student_information(self, student, course_id, request):
        """
        Returns a dict of students information:
        - url of the points detail
        - studentnumber
        - userprofile of student
        """
        student_info = {}

        student_detail = reverse('api:course-points-detail', kwargs={'version':2,
                               'course_id': course_id, 'pk': student.id,
                               }, request=request)

        student_link = reverse('api:user-detail', kwargs={'version':2,
                               'user_id': student.id,
                               }, request=request)

        student_info["studentnumber"] = student.student_id
        student_info["userprofile"] = student_link
        student_info["pointsdetails"] = student_detail

        return student_info


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


class CourseSubmissionDataViewSet(NestedViewSetMixin,
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

    def retrieve(self, request, course_id, version, user_id=None):
        profile = self.get_object()
        points = CachedPoints(self.instance, profile.user, self.content)
        ids = points.submission_ids(
            category_id=self._int_or_none(request.GET.get('category_id')),
            module_id=self._int_or_none(request.GET.get('module_id')),
            exercise_id=self._int_or_none(request.GET.get('exercise_id')),
            best=request.GET.get('best') != 'no',
        )
        serializer = self.get_serializer(
            Submission.objects.filter(id__in=ids),
            many=True
        )
        return Response(serializer.data)
