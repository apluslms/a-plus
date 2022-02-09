from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language, get_language_info

from authorization.permissions import ACCESS
from exercise.cache.content import CachedContent
from lib.helpers import remove_query_param_from_url, update_url_params
from lib.viewbase import BaseTemplateView
from userprofile.viewbase import UserProfileMixin
from .cache.students import CachedStudent
from .exceptions import TranslationNotFound
from .permissions import (
    CourseVisiblePermission,
    CourseModulePermission,
)
from .models import Course, CourseInstance, CourseModule, UserTagging


class CourseMixin(UserProfileMixin):
    course_kw = "course_slug"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.course = get_object_or_404(
            Course,
            url=self._get_kwarg(self.course_kw)
        )
        self.note("course")


class CourseBaseView(CourseMixin, BaseTemplateView):
    pass


class CourseInstanceBaseMixin(object):
    course_kw = CourseMixin.course_kw
    instance_kw = "instance_slug"
    course_permission_classes = (
        CourseVisiblePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.course_permission_classes))
        return perms

    # get_course_instance_object

    def get_resource_objects(self):
        super().get_resource_objects()
        user = self.request.user
        instance = self.get_course_instance_object()
        if instance is not None:
            self.instance = instance
            self.course = self.instance.course
            self.content = CachedContent(self.instance)
            self.user_course_data = None
            is_real_user = user.is_authenticated and not user.is_anonymous
            if is_real_user:
                self.user_course_data = self.instance.get_enrollment_for(user)
            self.is_student = self.instance.is_student(user)
            self.is_assistant = self.instance.is_assistant(user)
            self.is_teacher = self.instance.is_teacher(user)
            self.is_course_staff = self.is_teacher or self.is_assistant
            self.get_taggings = lambda: CachedStudent(instance, user.id).data['tag_slugs']
            self.url_without_language = remove_query_param_from_url(self.request.get_full_path(), 'hl')
            self.query_language = None
            self.user_language = None

            self.note(
                "course", "instance", "content", "user_course_data", "is_student", "is_assistant",
                "is_teacher", "is_course_staff", "get_taggings", "url_without_language",
                "query_language", "user_language"
            )

            # Try to find a language that is defined for this course instance
            # and apply it
            if self.instance.language:
                instance_languages = self.instance.language.strip('|').split('|')
                instance_def_language = instance_languages[0]
                instance_languages = set(instance_languages)

                languages = []
                if self.user_course_data and self.user_course_data.language:
                    languages.append(self.user_course_data.language)
                if is_real_user and user.userprofile.language:
                    languages.append(user.userprofile.language)
                languages.append(get_language())

                query_language = self.request.GET.get('hl')
                if query_language:
                    if query_language[:2] in instance_languages:
                        language = query_language
                        if languages:
                            self.user_language = languages[0]
                            if self.user_language[:2] != query_language[:2]:
                                self.query_language = query_language
                    else:
                        raise TranslationNotFound
                else:
                    for lang in languages:
                        if lang[:2] in instance_languages:
                            language = lang
                            break
                    else:
                        language = instance_def_language

                language = language[:2]
                # Override request.LANGUAGE_CODE. It is set in lib/middleware.py
                # (class LocaleMiddleware) based on the userprofile.language.
                # The middleware can not easily access the course context and
                # the language from the enrollment. That is fixed here.
                self.request.LANGUAGE_CODE = language
                translation.activate(language)

    def get_access_mode(self):
        access_mode = super().get_access_mode()

        if hasattr(self, 'instance'):
            # Loosen the access mode if instance is public
            show_for = self.instance.view_content_to
            is_public = show_for == CourseInstance.VIEW_ACCESS.PUBLIC
            access_mode_student = access_mode in (ACCESS.STUDENT, ACCESS.ENROLL)
            if is_public and access_mode_student:
                access_mode = ACCESS.ANONYMOUS

        return access_mode

    def handle_exception(self, exc):
        if isinstance(exc, TranslationNotFound):
            instance_languages = self.instance.language.strip("|").split("|")
            url = remove_query_param_from_url(self.request.get_full_path(), 'hl')
            for i, lang in enumerate(instance_languages):
                instance_languages[i] = {"name": get_language_info(lang)['name'], "url": update_url_params(url, {'hl' : lang})}
            return render(self.request, '404.html', {'error_msg': str(exc), 'languages': instance_languages}, status=404)
        return super().handle_exception(exc)

class CourseInstanceMixin(CourseInstanceBaseMixin, UserProfileMixin):
    def get_course_instance_object(self) -> CourseInstance:
        return get_object_or_404(
            CourseInstance.objects.prefetch_related('tabs'),
            url=self.kwargs[self.instance_kw],
            course__url=self.kwargs[self.course_kw],
        )

    def handle_no_permission(self):
        if (self.request.user.is_authenticated
                and not self.is_student
                and not self.is_course_staff
                and self.get_access_mode() in [ACCESS.STUDENT, ACCESS.ENROLLED]
                and self.instance.view_content_to == CourseInstance.VIEW_ACCESS.ENROLLED):
            # Redirect the user to the enrollment page instead of showing
            # a 403 Forbidden error, if:
            # - the user is signed in but not enrolled or staff
            # - the page is not a teacher page (e.g. edit course)
            # - the course is visible only to enrolled students
            return redirect(self.instance.get_url('enroll'))
        return super().handle_no_permission()


class CourseInstanceBaseView(CourseInstanceMixin, BaseTemplateView):
    pass


class EnrollableViewMixin(CourseInstanceMixin):
    access_mode = ACCESS.ENROLL

    def get_common_objects(self):
        self.enrolled = self.is_student
        self.enrollable = (
            self.profile
            and self.instance.is_enrollable(self.profile.user)
        )
        self.note('enrolled', 'enrollable')


class CourseModuleBaseMixin(object):
    module_kw = "module_slug"
    module_permissions_classes = (
        CourseModulePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.module_permissions_classes))
        return perms

    # get_course_module_object

    def get_resource_objects(self):
        super().get_resource_objects()
        self.module = self.get_course_module_object()
        self.note("module")


class CourseModuleMixin(CourseModuleBaseMixin, CourseInstanceMixin):
    def get_course_module_object(self):
        return get_object_or_404(
            CourseModule,
            url=self.kwargs[self.module_kw],
            course_instance=self.instance
        )


class CourseModuleBaseView(CourseModuleMixin, BaseTemplateView):
    pass
