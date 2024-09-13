from typing import Any, Dict, List, Union

from rest_framework import filters, viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework.permissions import IsAdminUser
from django.db.models import Q, QuerySet
from django.http import Http404
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from aplus.api import api_reverse
from edit_course.operations.configure import configure_from_url
from exercise.cache.content import ModuleContent, LearningObjectContent
from lib.api.constants import REGEX_INT, REGEX_INT_ME
from lib.api.filters import FieldValuesFilter
from lib.api.mixins import ListSerializerMixin, MeUserMixin
from lib.api.statistics import BaseStatisticsView
from lib.email_messages import email_course_instance
from lib.helpers import build_aplus_url
from news.models import News

from ..models import (
    Enrollment,
    USERTAG_EXTERNAL,
    USERTAG_INTERNAL,
    CourseInstance,
    CourseModule,
    StudentGroup,
    UserTag,
    UserTagging,
)
from .mixins import (
    CourseResourceMixin,
    CourseModuleResourceMixin,
)
from ..permissions import (
    JWTInstanceWritePermission,
    OnlyCourseTeacherPermission,
    IsCourseAdminOrUserObjIsSelf,
    OnlyEnrolledStudentOrCourseStaffPermission,
)
from .serializers import CourseBriefSerializer, CourseStudentGroupBriefSerializer, StudentBriefSerializer
from .full_serializers import (
    CourseNewsSerializer,
    CourseSerializer,
    CourseStatisticsSerializer,
    CourseStudentGroupSerializer,
    CourseUsertagSerializer,
    CourseUsertaggingsSerializer,
    CourseWriteSerializer,
    TreeCourseModuleSerializer,
)


class CourseViewSet(ListSerializerMixin,
                    CourseResourceMixin,
                    viewsets.ModelViewSet):
    """
    The `courses` endpoint returns information about all course instances.

    Operations
    ----------

    `GET /courses/`:
        returns a list of all courses.

    `GET /courses/<course_id>/`:
        returns the details of a specific course.

    `POST /courses/`:
        creates a new course instance. Requires admin privileges. Following attributes can be given:

    * `name`: Name of the course.
    * `code`: Course code. If a course with this code does not exist, it will be created.
    * `course_url`: URL slug for the course
    * `instance_name`
    * `url`: course instance URL. If this is not given, the URL will be generated from instance_name.
    * `language`
    * `starting_time`
    * `ending_time`
    * `visible_to_students`
    * `configure_url`: the configuration URL for MOOC grader.
    * `teachers`: list of teacher usernames on the course.
      If given user does not exist, the user will be created.
      Only the username of created user is set.
      If user logs in using external authentication service such as Haka,
      the other user attributes will be updated on first login.

    `PUT /courses/<course_id>/`:
        modifies the attributes of a specific course. Attributes that are modified:
        `instance_name`, `url`, `language`, `starting_time`, `ending_time`,
        `visible_to_students`, `configure_url`, `teachers`.
        Only the course instance data can be modified. Course code, name, or URL
        cannot be modified using this API. Requires admin privileges.

    `POST /courses/<course_id>/notify_update/`:
        triggers a course update and returns JSON {errors: <error list>, success: <bool>}.
        Following attributes can be given:

    * `email_on_error`: whether to send an email to instance staff on error

    `POST /courses/<course_id>/send_mail/`:
        sends an email to course instance's technical contacts (or teachers if
        there are no technical contacts). Empty response on success, otherwise
        returns the error. Following attributes can be given:

    * `subject`: email subject
    * `message`: email body
    """
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

    def get_permissions(self):
        if self.request.method == 'GET':
            self.permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
        else:
            self.permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [IsAdminUser]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method in ('POST', 'PUT'):
            return CourseWriteSerializer
        return super().get_serializer_class()

    # get_permissions lambda overwrites the normal version used for the above methods
    @action(detail=True, methods=["post"], get_permissions=lambda: [JWTInstanceWritePermission()])
    def notify_update(self, request, *args, **kwargs):
        try:
            success, errors = configure_from_url(self.instance, self.instance.configure_url)
        except Exception as e:
            success = False
            errors = [format_lazy(
                _('COURSE_CONFIG_ERROR -- {error!s}'),
                error=e,
            )]

        if errors and request.POST.get("email_on_error", True):
            if success:
                subject = format_lazy(_("COURSE_UPDATE_WARNINGS_SUBJECT -- {instance}"), instance=self.instance)
            else:
                subject = format_lazy(_("COURSE_UPDATE_ERRORS_SUBJECT -- {instance}"), instance=self.instance)
            message = "\n".join(str(e) for e in errors)
            try:
                success = email_course_instance(self.instance, str(subject), message)
            except Exception as e:
                errors.append(_("ERROR_EMAIL_FAILED") + f": {e}")
            else:
                if not success:
                    errors.append(_("ERROR_EMAIL_FAILED"))

        return Response({
            "errors": errors,
            "success": success
        })

    # get_permissions lambda overwrites the normal version used for the above methods
    @action(detail=True, methods=["post"], get_permissions=lambda: [JWTInstanceWritePermission()])
    def send_mail(self, request, *args, **kwargs):
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        try:
            success = email_course_instance(self.instance, subject, message)
        except ValueError as e:
            return Response(str(e))
        except Exception as e:
            return Response(str(e))
        if success:
            return Response()
        return Response(_("SEND_EMAIL_FAILED"))


class CourseExercisesViewSet(NestedViewSetMixin,
                             CourseModuleResourceMixin,
                             CourseResourceMixin,
                             viewsets.ViewSet):
    """
    The `exercises` endpoint returns information about the course modules
    defined in the course instance, and the exercises defined in those modules.

    Operations
    ----------

    `GET /courses/<course_id>/exercises/`:
        returns a list of all modules and their exercises.

    `GET /courses/<course_id>/exercises/<exercisemodule_id>/`:
        returns the details and exercises of a specific module.
    """
    lookup_url_kwarg = 'exercisemodule_id'
    lookup_value_regex = REGEX_INT
    parent_lookup_map = {'course_id': 'course_instance.id'}

    def __recurse_exercises(
            self,
            module: Union[ModuleContent, LearningObjectContent],
            exercises: List[Dict[str, Any]],
            ) -> List[Dict[str, Any]]:
        for child in module.children:
            if child.submittable:
                exercise_dictionary = {
                    'id': child.id,
                    'url': build_aplus_url(
                        api_reverse('exercise-detail', kwargs={'exercise_id': child.id}),
                        True,
                    ),
                    'html_url': build_aplus_url(child.link, True),
                    'display_name': child.name,
                    'max_points': child.max_points,
                    'max_submissions': child.max_submissions,
                    'hierarchical_name': child.hierarchical_name,
                    'difficulty': child.difficulty,
                    'has_submittable_files': child.has_submittable_files,
                }
                exercises.append(exercise_dictionary)

            # Both exercises and chapters may have children.
            # (Chapters are "non-submittable exercises" in the cache.)
            exercises = self.__recurse_exercises(child, exercises)

        return exercises

    def __module_to_dict(self, module: ModuleContent, **kwargs) -> Dict[str, Any]:
        kwargs['exercisemodule_id'] = module.id
        module_dictionary = {
            'id': module.id,
            'url': build_aplus_url(api_reverse("course-exercises-detail", kwargs=kwargs), True),
            'html_url': build_aplus_url(module.link, True),
            'display_name': module.name,
            'is_open': CourseModule.check_is_open(
                module.reading_opening_time,
                module.opening_time,
                module.closing_time,
            ),
            'reading_opening_time': module.reading_opening_time,
            'opening_time': module.opening_time,
            'closing_time': module.closing_time,
        }
        module_dictionary['exercises'] = self.__recurse_exercises(module, [])
        return module_dictionary

    def list(self, request, *args, **kwargs) -> Response:
        modules = []
        for module in self.content.data.modules:
            if module.is_visible():
                modules.append(self.__module_to_dict(module, **kwargs))
        return Response({"count": len(modules), "next": None, "previous": None, 'results': modules})

    def retrieve(self, request, *args, **kwargs) -> Response:
        # try to get the module list index
        entry = self.content.data.module_index.get(int(kwargs['exercisemodule_id']))
        if entry is None:
            raise Http404()

        return Response(self.__module_to_dict(entry, **kwargs))


class CourseExerciseTreeViewSet(CourseResourceMixin,
                                viewsets.ViewSet):
    """
    The `tree` endpoint returns the modules, chapters and exercises of the
    course in a sorted tree-like structure.

    Operations
    ----------

    `GET /courses/<course_id>/tree/`:
        returns the tree.
    """

    # To build the tree, this viewset uses the `CachedContent` class, which
    # contains the course's chapters and exercises in a hierarchical structure.
    # The CachedContent instance is accessed through the `self.content`
    # attribute, which is defined in the `CourseInstanceBaseMixin` base class.

    serializer_class = TreeCourseModuleSerializer

    def list(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            self.content.data.modules,
            many=True,
            context={ 'request': request }
        )
        response_data = { 'modules': serializer.data }
        return Response(response_data)


class CourseStudentsViewSet(NestedViewSetMixin,
                            MeUserMixin,
                            CourseResourceMixin,
                            viewsets.ReadOnlyModelViewSet):
    """
    The `students` endpoint returns information about the students that have
    enrolled in the course.

    Operations
    ----------

    `GET /courses/<course_id>/students/`:
        returns a list of all students.

    `GET /courses/<course_id>/students/<user_id>/`:
        returns the details of a specific student.

    `GET /courses/<course_id>/students/me/`:
        returns the details of the current user.

    `DELETE /courses/<course_id>/students/<user_id>/`:
        removes the enrollment. Students cannot unenroll themselves.

    - URL parameters:
        - `status`: the new status for the enrollment. `REMOVED` and `BANNED`
            are currently supported.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsCourseAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsCourseAdminOrUserObjIsSelf,
        filters.SearchFilter,
        FieldValuesFilter,
    )
    search_fields = ['user__first_name', 'user__last_name', 'student_id', 'user__email']
    field_values_map = {'id': 'user_id', 'student_id': 'student_id', 'email': 'user__email'}
    lookup_field = 'user_id' # UserPofile.user.id
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    serializer_class = StudentBriefSerializer

    def get_queryset(self):
        return self.instance.students

    def destroy(self, request, *args, **kwargs):
        if not self.is_course_staff:
            return Response(
                'Student self-unenrollment is not allowed. Contact course '
                'staff if you wish to remove your enrollment.',
                status=status.HTTP_403_FORBIDDEN
            )

        status_arg = self.request.GET.get('status')
        if status_arg not in Enrollment.ENROLLMENT_STATUS.keys():
            return Response(
                'Invalid status',
                status=status.HTTP_400_BAD_REQUEST
            )
        status_code = getattr(Enrollment.ENROLLMENT_STATUS, status_arg)

        if status_code == Enrollment.ENROLLMENT_STATUS.ACTIVE:
            return Response(
                'Enrollments cannot be activated via this API',
                status=status.HTTP_400_BAD_REQUEST
            )
        # if status_code != Enrollment.ENROLLMENT_STATUS.REMOVED and not self.is_course_staff:
        #     return Response(
        #         'Students can only unenroll themselves (status=REMOVED) via this API',
        #         status=status.HTTP_403_FORBIDDEN
        #     )

        user = self.get_object().user
        enrollment = self.instance.get_enrollment_for(user)
        enrollment.status = status_code
        enrollment.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseUsertagsViewSet(NestedViewSetMixin,
                            CourseModuleResourceMixin,
                            CourseResourceMixin,
                            mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.DestroyModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    """
    The `usertags` endpoint returns information about the student tags defined
    in the course, and can also create and delete student tags.

    Operations
    ----------

    `GET /courses/<course_id>/usertags/`:
        returns a list of all student tags.

    `GET /courses/<course_id>/usertags/<usertag_id>/`:
        returns the details of a specific student tag.

    `POST /courses/<course_id>/usertags/`:
        creates a new student tag.

    - Body data:
        - `slug`
        - `name`
        - `description`
        - `visible_to_students`
        - `color`

    `DELETE /courses/<course_id>/usertags/<usertag_id>/`:
        deletes a specific student tag.
    """
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
    """
    The `taggings` endpoint returns information about the student tags applied
    to the student of the course, and can also apply tags to users and remove
    them.

    Operations
    ----------

    `GET /courses/<course_id>/taggings/`:
        returns a list of all student taggings.

    `GET /courses/<course_id>/taggings/<usertag_id>/`:
        returns the details of a specific student tagging.

    `POST /courses/<course_id>/taggings/`:
        creates a new student tagging.

    - Body data:
        - `tag.slug`
        - One of:
            - `user.id`
            - `user.student_id`
            - `user.username`
            - `user.email`

    `DELETE /courses/<course_id>/taggings/`:
        deletes a user tag from one or more students.

    - URL parameters:
        - `tag_id`: id of the tag to be deleted
        - `user_id`: id of the student from which the tag will be deleted
            (repeated for each student)

    `DELETE /courses/<course_id>/taggings/<usertag_id>/`:
        deletes a specific student tagging.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyCourseTeacherPermission,
    ]
    lookup_field = 'id'
    lookup_url_kwarg = 'usertag_id'
    serializer_class = CourseUsertaggingsSerializer
    queryset = (
        UserTagging.objects
        .select_related('tag', 'user', 'user__user')
        .only('tag__id', 'tag__course_instance', 'tag__name', 'tag__slug',
            'user__user__id', 'user__user__email', 'user__user__username', 'user__student_id',
            'user__user__first_name', 'user__user__last_name', 'user__organization',
            'course_instance__id'
        )
        .order_by('user__user__id')
        .all()
    )
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


class CourseOwnStudentGroupsViewSet(NestedViewSetMixin,
                                    CourseResourceMixin,
                                    viewsets.ReadOnlyModelViewSet):
    """
    The `mygroups` endpoint returns information about the user's own student
    groups defined in the course. Teachers receive only their own groups as
    well.

    Operations
    ----------

    `GET /courses/<course_id>/mygroups/`:
        returns a list of all groups.

    `GET /courses/<course_id>/mygroups/<id>/`:
        returns the details of a specific group.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyEnrolledStudentOrCourseStaffPermission,
    ]
    serializer_class = CourseStudentGroupBriefSerializer
    parent_lookup_map = {'course_id': 'course_instance.id'}

    def get_queryset(self) -> QuerySet[StudentGroup]:
        return (
            StudentGroup.objects.filter(
                course_instance=self.instance,
                members=self.request.user.userprofile,
            )
            .select_related('course_instance')
        )


class CourseStudentGroupsViewSet(NestedViewSetMixin,
                                 CourseResourceMixin,
                                 viewsets.ReadOnlyModelViewSet):
    """
    The `mygroups` endpoint returns information about all student groups
    defined in the course.

    Operations
    ----------

    `GET /courses/<course_id>/groups/`:
        returns a list of all groups.

    `GET /courses/<course_id>/groups/<id>/`:
        returns the details of a specific group.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyCourseTeacherPermission,
    ]
    serializer_class = CourseStudentGroupSerializer
    queryset = (
        StudentGroup.objects
        .select_related('course_instance')
    )
    parent_lookup_map = {'course_id': 'course_instance.id'}

class CourseNewsViewSet(NestedViewSetMixin,
                        CourseResourceMixin,
                        viewsets.ReadOnlyModelViewSet):
    """
    The `news` endpoint returns information about course news.

    Operations
    ----------

    `GET /courses/<course_id>/news/`:
        returns a list of all news items.

    `GET /courses/<course_id>/news/<id>/`:
        returns the details of a specific news.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        OnlyEnrolledStudentOrCourseStaffPermission,
    ]
    serializer_class = CourseNewsSerializer
    parent_lookup_map = {'course_id': 'course_instance.id'}

    def get_queryset(self) -> QuerySet[News]:
        user = self.request.user
        AUDIENCE = CourseInstance.ENROLLMENT_AUDIENCE
        queryset = News.objects.select_related('course_instance')

        if not user.is_superuser and not self.instance.is_course_staff(user):
            # Filter out unpublished news based on the publish date
            queryset = queryset.filter(publish__lte=timezone.now())
            if user.userprofile.is_external:
                return queryset.filter(
                    Q(audience=AUDIENCE.ALL_USERS) |
                    Q(audience=AUDIENCE.EXTERNAL_USERS)
                )
            return queryset.filter(
                Q(audience=AUDIENCE.ALL_USERS) |
                Q(audience=AUDIENCE.INTERNAL_USERS)
            )
        return queryset


class CourseStatisticsView(BaseStatisticsView):
    """
    Returns submission statistics for a course, over a given time window.

    Returns the following attributes:

    - `submission_count`: total number of submissions.
    - `submitters`: number of users submitting.

    Operations
    ----------

    `GET /courses/<course_id>/statistics/`:
        returns the statistics for the given course.

    - URL parameters:
        - `endtime`: date and time in ISO 8601 format indicating the end point
          of time window we are interested in. Default: now.
        - `starttime`: date and time in ISO 8601 format indicating the start point
          of time window we are interested in. Default: one day before endtime
    """

    serializer_class = CourseStatisticsSerializer

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        course_id = self.kwargs['course_id']
        return queryset.filter(
            exercise__course_module__course_instance=course_id,
        )

    def get_object(self):
        obj = super().get_object()
        obj.update({ 'course_id': self.kwargs['course_id'] })
        return obj
