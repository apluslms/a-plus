from rest_framework import generics, permissions, viewsets, status, mixins
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.reverse import reverse
from rest_framework_extensions.mixins import NestedViewSetMixin

from lib.viewbase import BaseMixin
from lib.api.mixins import ListSerializerMixin, MeUserMixin
from lib.api.constants import REGEX_INT, REGEX_INT_ME
from userprofile.models import UserProfile
from userprofile.permissions import IsAdminOrUserObjIsSelf

from ..models import (
    USERTAG_EXTERNAL,
    USERTAG_INTERNAL,
    CourseInstance,
    CourseModule,
    UserTag,
    UserTagging,
)
from .mixins import (
    CourseResourceMixin,
    CourseModuleResourceMixin,
)
from ..permissions import (
    OnlyCourseTeacherPermission,
    IsCourseAdminOrUserObjIsSelf,
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
    lookup_field = 'user_id' # UserPofile.user.id
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {'course_id': 'enrolled.id'}
    serializer_class = StudentBriefSerializer
    queryset = UserProfile.objects.all()


class CourseUsertagsViewSet(NestedViewSetMixin,
                            CourseModuleResourceMixin,
                            CourseResourceMixin,
                            mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.DestroyModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyCourseTeacherPermission,
    ]
    lookup_field = 'id'
    lookup_url_kwarg = 'usertag_id'
    serializer_class = CourseUsertagSerializer
    queryset = UserTag.objects.all()
    parent_lookup_map = {'course_id': 'course_instance_id'}

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        tags = [USERTAG_INTERNAL, USERTAG_EXTERNAL]
        tags.extend(queryset.all())
        page = self.paginate_queryset(tags)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({ 'course_id': self.kwargs['course_id'] })
        return context


class CourseUsertaggingsViewSet(NestedViewSetMixin,
                                CourseModuleResourceMixin,
                                CourseResourceMixin,
                                mixins.CreateModelMixin,
                                mixins.RetrieveModelMixin,
                                mixins.DestroyModelMixin,
                                mixins.ListModelMixin,
                                viewsets.GenericViewSet):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyCourseTeacherPermission,
    ]
    lookup_field = 'id'
    lookup_url_kwarg = 'usertag_id'
    serializer_class = CourseUsertaggingsSerializer
    queryset = ( UserTagging.objects
                 .select_related('tag', 'user', 'user__user')
                 .only('tag__id', 'tag__course_instance', 'tag__name', 'tag__slug',
                       'user__user__id', 'user__user__email', 'user__user__username', 'user__student_id',
                       'course_instance__id')
                 .order_by('user__user__id')
                 .all() )
    parent_lookup_map = {'course_id': 'course_instance_id'}

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({ 'course_id': self.kwargs['course_id'] })
        return context

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        tag_id = self.request.GET.get('tag_id')
        if tag_id is not None:
            queryset = queryset.filter(tag__id=tag_id)
        user_id = self.request.GET.get('user_id')
        if user_id is not None:
            queryset = queryset.filter(user__user__id=user_id)
        return queryset

    def destroy_many(self, request, **kwargs):
        '''Destroy taggings based on GET query parameters.

        The detail view requires the ID of the tagging, but this method can
        search for the tagging with other parameters.
        '''
        filter_args = {}
        tag_id = self.request.GET.get('tag_id')
        if tag_id:
            filter_args['tag__id'] = tag_id
        else:
            tag_slug = self.request.GET.get('tag_slug')
            if not tag_slug:
                raise ParseError(detail='Either "tag_id" or "tag_slug" query parameter must be supplied.')
            filter_args['tag__slug'] = tag_slug
        user_ids = self.request.GET.getlist('user_id')
        if not user_ids:
            raise ParseError(detail='One or more user IDs must be supplied with the "user_id" query parameter.')
        filter_args['user__user__id__in'] = user_ids

        self.get_queryset().filter(**filter_args).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

