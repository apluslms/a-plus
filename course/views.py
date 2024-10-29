import datetime
import icalendar
from urllib.parse import unquote
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, translate_url
from django.utils import html, timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import format_lazy
from django.utils.translation import check_for_language
from django.utils.translation import gettext_lazy as _

from authorization.permissions import ACCESS
from exercise.cache.hierarchy import NoSuchContent
from exercise.models import LearningObject
from lib.helpers import settings_text, remove_query_param_from_url, is_ajax
from lib.viewbase import BaseTemplateView, BaseRedirectMixin, BaseFormView, BaseView, BaseRedirectView
from userprofile.viewbase import UserProfileView
from .forms import GroupsForm, GroupSelectForm
from .models import Course, CourseInstance, CourseModule, Enrollment
from .permissions import EnrollInfoVisiblePermission
from .renders import group_info_context
from .viewbase import CourseModuleBaseView, CourseInstanceMixin, EnrollableViewMixin, CourseMixin


class HomeView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "course/index.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.welcome_text = settings_text('WELCOME_TEXT')
        self.internal_user_label = settings_text('INTERNAL_USER_LABEL')
        self.external_user_label = settings_text('EXTERNAL_USER_LABEL')
        self.show_language_toggle = True
        my_instances = []
        all_instances = []
        end_threshold = timezone.now() - datetime.timedelta(days=30)
        user = self.request.user
        is_logged_in = False

        if user and user.is_authenticated:
            is_logged_in = True
            for instance in CourseInstance.objects.get_teaching(user.userprofile).all().filter(
                    ending_time__gte=end_threshold
                ):
                my_instances.append(instance)

            for instance in CourseInstance.objects.get_assisting(user.userprofile).all().filter(
                    ending_time__gte=end_threshold
                ):
                if instance not in my_instances:
                    my_instances.append(instance)

            for instance in CourseInstance.objects.get_enrolled(user.userprofile).all().filter(
                    ending_time__gte=end_threshold,
                    visible_to_students=True,
                ):
                if instance not in my_instances:
                    my_instances.append(instance)

        all_instances = CourseInstance.objects.get_visible(user).filter(ending_time__gte=end_threshold)
        all_instances = [c for c in all_instances if c not in my_instances]

        self.all_instances = all_instances
        self.my_instances = my_instances
        self.is_logged_in = is_logged_in

        self.note("welcome_text",
            "internal_user_label",
            "external_user_label",
            "my_instances",
            "all_instances",
            "is_logged_in",
            "show_language_toggle",
        )


class ArchiveView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "course/archive.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.instances = CourseInstance.objects.get_visible(self.request.user)
        self.show_language_toggle = True
        self.note("instances", "show_language_toggle")

class CourseInstancesView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "course/course_instances.html"

    def get_common_objects(self, **kwargs: Any) -> None:
        course = get_object_or_404(Course, url=self.kwargs['course_slug'])
        self.instances = []
        self.msg = ""
        if CourseInstance.objects.filter(course=course).exists():
            self.instances = (
                CourseInstance.objects
                .get_visible(self.request.user)
                .filter(course=course)
                .order_by('-starting_time')
            )
            self.msg = _('COURSE_INSTANCES_NOT_VISIBLE_TO_STUDENTS')
        else:
            self.msg = _('NO_COURSE_INSTANCES_OF_COURSE')

        self.note("instances", "msg")

class LastInstanceView(CourseMixin, BaseRedirectView):
    access_mode = ACCESS.ANONYMOUS

    def get_resource_objects(self):
        super().get_resource_objects()
        now = timezone.now()
        course_instances = CourseInstance.objects.filter(course=self.course).order_by('-starting_time')
        instance_ids_with_open_course_modules = set(
            CourseModule.objects.filter(
                course_instance__course=self.course,
                status__in=(CourseModule.STATUS.READY, CourseModule.STATUS.UNLISTED),
                opening_time__lte=now,
            )
            .values_list('course_instance_id', flat=True)
            .order_by()
            .distinct()
        )

        latest_open = None
        latest_visible = None
        latest_hidden = None
        for instance in course_instances:
            if instance.visible_to_students:
                if (instance.id in instance_ids_with_open_course_modules
                        and instance.starting_time <= now
                        ):
                    latest_open = instance
                    break
                latest_visible = latest_visible or instance
            else:
                latest_hidden = latest_hidden or instance

        if latest_open:
            self.course_instance = latest_open
        elif latest_visible:
            self.course_instance = latest_visible
        elif latest_hidden and latest_hidden.is_course_staff(self.request.user):
            self.course_instance = latest_hidden
        else:
            raise Http404(_('NO_COURSE_INSTANCES_OF_COURSE'))

    def get(self, request, *args, **kwargs):
        return self.redirect(self.course_instance.get_display_url())

class InstanceView(EnrollableViewMixin, BaseRedirectMixin, BaseTemplateView):
    access_mode = ACCESS.STUDENT
    # ACCESS.STUDENT requires users to log in, but the access mode is dropped
    # in public courses. CourseVisiblePermission has more restrictions as well.
    template_name = "course/course.html"

    @property
    def instance_max_group_size(self) -> int:
        return self.points.total().max_group_size

    @property
    def instance_min_group_size(self) -> int:
        return self.points.total().min_group_size

    def get(self, request, *args, **kwargs):
        # external LTI Tool Providers may return the user to the course instance view
        # with a message given in GET query parameters
        lti_error_msg = request.GET.get('lti_errormsg')
        lti_msg = request.GET.get('lti_msg')
        # message HTML is not escaped in the templates so escape it here
        if lti_error_msg:
            messages.error(request, html.escape(lti_error_msg))
        elif lti_msg:
            messages.info(request, html.escape(lti_msg))

        # PENDING student has enrolled, but not yet responded to the enrollment questionnaire.
        if request.user.is_authenticated:
            enrollment = self.user_course_data
            if enrollment and enrollment.status == Enrollment.ENROLLMENT_STATUS.PENDING:
                exercise = LearningObject.objects.find_enrollment_exercise(
                    self.instance, self.profile.is_external)
                # For PENDING student, it should not be possible for exercise to be null,
                # but better be careful. In that case, proceeding to the course seems OK.
                if exercise:
                    return self.redirect(exercise.get_absolute_url())

        return super().get(request, *args, **kwargs)


class Enroll(EnrollableViewMixin, BaseRedirectMixin, BaseTemplateView):
    permission_classes = [EnrollInfoVisiblePermission]
    course_permission_classes = []
    template_name = "course/enroll.html"

    def post(self, request, *args, **kwargs):

        if self.is_student or not self.enrollable:
            messages.error(self.request, _('ENROLLMENT_ERROR_CANNOT_ENROLL_OR_ALREADY_ENROLLED'))
            raise PermissionDenied()

        if not self.instance.is_enrollment_open():
            messages.error(self.request, _('ENROLLMENT_ERROR_ENROLLMENT_NOT_OPEN'))
            raise PermissionDenied()

        # Support enrollment questionnaires.
        exercise = LearningObject.objects.find_enrollment_exercise(
            self.instance, self.profile.is_external)
        if exercise:
            self.instance.enroll_student(self.request.user, from_sis=False, use_pending=True)
            return self.redirect(exercise.get_absolute_url())

        self.instance.enroll_student(self.request.user)
        return self.redirect(self.instance.get_absolute_url())


class Unenroll(CourseInstanceMixin, BaseView):
    access_mode = ACCESS.ENROLLED

    def post(self, request, *args, **kwargs):
        enrollment = self.user_course_data
        if (
            enrollment
            and enrollment.role == Enrollment.ENROLLMENT_ROLE.STUDENT
            and enrollment.status == Enrollment.ENROLLMENT_STATUS.ACTIVE
        ):
            enrollment.status = Enrollment.ENROLLMENT_STATUS.REMOVED
            enrollment.save()
            messages.success(
                self.request,
                format_lazy(
                    _('UNENROLL_SUCCESS -- {course}'),
                    course=self.course.code,
                ),
            )
            return HttpResponseRedirect(reverse('home'))
        messages.error(self.request, _('UNENROLL_ERROR_ONLY_ENROLLED'))
        raise PermissionDenied()


class ModuleView(CourseModuleBaseView):
    template_name = "course/module.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.now = timezone.now()
        try:
            self.children = self.points.flat_module(self.module)
            cur, _tree, prev, nex = self.points.find(self.module)
            self.previous = prev
            self.current = cur
            self.next = nex
        except NoSuchContent as exc:
            raise Http404 from exc
        self.note('now', 'children', 'previous', 'current', 'next')


class CalendarExport(CourseInstanceMixin, BaseView):

    def get(self, request, *args, **kwargs):
        cal = icalendar.Calendar()
        cal.add('prodid', '-// {} calendar //'.format(settings.BRAND_NAME))
        cal.add('version', '2.0')
        for module in self.instance.course_modules.exclude(status__exact=CourseModule.STATUS.HIDDEN):
            event = icalendar.Event()
            event.add('summary', module.name)
            event.add('dtstart',
                module.closing_time - datetime.timedelta(hours=1))
            event.add('dtend', module.closing_time)
            event.add('dtstamp', module.closing_time)
            event['uid'] = "module/" + str(module.id) + "/A+"
            cal.add_component(event)

        return HttpResponse(cal.to_ical(),
            content_type="text/calendar; charset=utf-8")


class GroupsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.ENROLLED
    template_name = "course/groups.html"
    form_class = GroupsForm

    def get_common_objects(self):
        super().get_common_objects()
        self.enrollment = self.user_course_data
        self.groups = list(self.profile.groups.filter(course_instance=self.instance))
        self.note('enrollment','groups')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["profile"] = self.profile
        kwargs["instance"] = self.instance
        kwargs["content"] = self.content
        return kwargs

    def get_success_url(self):
        return self.instance.get_url('groups')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('NEW_STUDENT_GROUP_CREATED'))
        return super().form_valid(form)


class GroupSelect(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.ENROLLED
    form_class = GroupSelectForm
    template_name = "course/_group_info.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["profile"] = self.profile
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        return self.instance.get_absolute_url()

    def get(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    def form_invalid(self, form):
        return HttpResponse('Invalid group selection')

    def form_valid(self, form):
        enrollment = form.save()
        if is_ajax(self.request):
            return self.render_to_response(self.get_context_data(
                **group_info_context(enrollment.selected_group, self.profile)))
        return super().form_valid(form)


class LanguageView(CourseInstanceMixin, BaseView):

    def post(self, request, *args, **kwargs):
        LANGUAGE_PARAMETER = 'language'
        # pylint: disable-next=redefined-builtin
        next = remove_query_param_from_url(request.POST.get('next', request.GET.get('next')), 'hl')
        if ((next or not is_ajax(request)) and
                not url_has_allowed_host_and_scheme(url=next,
                                allowed_hosts={request.get_host()},
                                require_https=request.is_secure())):
            next = remove_query_param_from_url(request.META.get('HTTP_REFERER'), 'hl')
            next = next and unquote(next)  # HTTP_REFERER may be encoded.
            if not url_has_allowed_host_and_scheme(url=next,
                                allowed_hosts={request.get_host()},
                                require_https=request.is_secure()):
                next = '/'
        response = HttpResponseRedirect(next) if next else HttpResponse(status=204)
        if request.method == 'POST':
            lang_code = request.POST.get(LANGUAGE_PARAMETER)
            if lang_code and check_for_language(lang_code):
                if next:
                    next_trans = translate_url(next, lang_code)
                    if next_trans != next:
                        response = HttpResponseRedirect(next_trans)
                if request.user.is_authenticated:
                    enrollment = self.user_course_data
                    if enrollment:
                        enrollment.language = lang_code
                        enrollment.save()
                    else:
                        userprofile = request.user.userprofile
                        userprofile.language = lang_code
                        userprofile.save()
                else:
                    response.set_cookie(
                        settings.LANGUAGE_COOKIE_NAME, lang_code,
                        max_age=settings.LANGUAGE_COOKIE_AGE,
                        path=settings.LANGUAGE_COOKIE_PATH,
                        domain=settings.LANGUAGE_COOKIE_DOMAIN,
                    )
                request.REQUEST_LANG = lang_code
        return response
