from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin
from lib.api import ListSerializerMixin

from ..models import (
    CourseInstance,
    CourseModule,
)
from .serializers import (
    CourseBriefSerializer,
    CourseSerializer,
    CourseModuleSerializer,
)
from userprofile.models import UserProfile
from userprofile.api.serializers import UserBriefSerialiser


class CourseViewSet(ListSerializerMixin, viewsets.ReadOnlyModelViewSet):
    queryset = CourseInstance.objects.filter(visible_to_students=True)
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'course_id'
    listserializer_class = CourseBriefSerializer
    serializer_class = CourseSerializer


class CourseExercisesViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'exercisemodule_id'
    serializer_class = CourseModuleSerializer
    queryset = CourseModule.objects.all()
    parent_lookup_map = {'course_id': 'course_instance.id'}


class CourseStudentsViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'user_id'
    serializer_class = UserBriefSerialiser
    queryset = UserProfile.objects.all()
    parent_lookup_map = {'course_id': 'enrolled.id'}
