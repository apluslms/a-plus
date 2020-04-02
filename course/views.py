import datetime

import icalendar
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import html
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from authorization.permissions import ACCESS
from exercise.cache.hierarchy import NoSuchContent
from exercise.models import LearningObject
from lib.helpers import settings_text
from lib.viewbase import BaseTemplateView, BaseRedirectMixin, BaseFormView, BaseView
from userprofile.viewbase import UserProfileView
from .forms import GroupsForm, GroupSelectForm, EnrollStudentsForm
from .models import CourseInstance, Enrollment
from .permissions import EnrollInfoVisiblePermission
from .renders import group_info_context
from .viewbase import CourseModuleBaseView, CourseInstanceMixin, EnrollableViewMixin


class HomeView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "course/index.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.welcome_text = settings_text('WELCOME_TEXT')
        self.internal_user_label = settings_text('INTERNAL_USER_LABEL')
        self.external_user_label = settings_text('EXTERNAL_USER_LABEL')
        self.instances = []
        prio2 = []
        treshold = timezone.now() - datetime.timedelta(days=10)
        for instance in CourseInstance.objects.get_visible(self.request.user)\
                .filter(ending_time__gte=timezone.now()):
            if instance.starting_time > treshold:
                self.instances += [instance]
            else:
                prio2 += [instance]
        self.instances += prio2
        self.note("welcome_text", "internal_user_label", "external_user_label", "instances")


class ArchiveView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "course/archive.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.instances = CourseInstance.objects.get_visible(self.request.user)
        self.note("instances")

class InstanceView(EnrollableViewMixin, BaseTemplateView):
    access_mode = ACCESS.STUDENT
    # ACCESS.STUDENT requires users to log in, but the access mode is dropped
    # in public courses. CourseVisiblePermission has more restrictions as well.
    template_name = "course/course.html"

    def handle_no_permission(self):
        if self.request.user.is_authenticated \
                and self.instance.view_content_to == CourseInstance.VIEW_ACCESS.ENROLLED:
            # The course instance is visible to only enrolled students, so
            # redirect the user to the enroll page instead of showing
            # a 403 Forbidden error.
            return redirect(self.instance.get_url('enroll'))
        return super().handle_no_permission()

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

        return super().get(request, *args, **kwargs)


class Enroll(EnrollableViewMixin, BaseRedirectMixin, BaseTemplateView):
    permission_classes = [EnrollInfoVisiblePermission]
    course_permission_classes = []
    template_name = "course/enroll.html"

    def post(self, request, *args, **kwargs):

        if self.is_student or not self.enrollable:
            messages.error(self.request, _("You cannot enroll, or have already enrolled, in this course."))
            raise PermissionDenied()

        if not self.instance.is_enrollment_open():
            messages.error(self.request, _("The enrollment is not open."))
            raise PermissionDenied()

        # Support enrollment questionnaires.
        exercise = LearningObject.objects.find_enrollment_exercise(
            self.instance, self.profile)
        if exercise:
            return self.redirect(exercise.get_absolute_url())

        self.instance.enroll_student(self.request.user)
        return self.redirect(self.instance.get_absolute_url())


class ModuleView(CourseModuleBaseView):
    template_name = "course/module.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.now = timezone.now()
        try:
            self.children = self.content.flat_module(self.module)
            cur, tree, prev, nex = self.content.find(self.module)
            self.previous = prev
            self.current = cur
            self.next = nex
        except NoSuchContent:
            raise Http404
        self.note('now', 'children', 'previous', 'current', 'next')


class CalendarExport(CourseInstanceMixin, BaseView):

    def get(self, request, *args, **kwargs):
        cal = icalendar.Calendar()
        cal.add('prodid', '-// {} calendar //'.format(settings.BRAND_NAME))
        cal.add('version', '2.0')
        for module in self.instance.course_modules.all():
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
        self.enrollment = self.instance.get_enrollment_for(self.request.user)
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
        messages.success(self.request, _("A new student group was created."))
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
        if self.request.is_ajax():
            return self.render_to_response(self.get_context_data(
                **group_info_context(enrollment.selected_group, self.profile)))
        return super().form_valid(form)


class EnrollStudentsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    form_class = EnrollStudentsForm
    template_name = "course/staff/enroll_students.html"

    def form_valid(self, form):
        for profile in form.cleaned_data["user_profiles"]:
            self.instance.enroll_student(profile.user)
        return super().form_valid(form)

    def get_success_url(self):
        return self.instance.get_url('participants')
