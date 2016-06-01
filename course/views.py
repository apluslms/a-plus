import datetime
import logging

import icalendar
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import View

from exercise.models import LearningObject
from lib.helpers import settings_text
from lib.viewbase import BaseTemplateView, BaseRedirectView
from userprofile.viewbase import ACCESS, UserProfileView
from .viewbase import CourseBaseView, CourseInstanceBaseView, \
    CourseModuleBaseView, CourseInstanceMixin, EnrollableViewMixin
from .models import CourseInstance


logger = logging.getLogger("course.views")


class HomeView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "course/index.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.welcome_text = settings_text(self.request, 'WELCOME_TEXT')
        self.internal_user_label = settings_text(self.request, 'INTERNAL_USER_LABEL')
        self.external_user_label = settings_text(self.request, 'EXTERNAL_USER_LABEL')
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


class ProfileView(UserProfileView):
    template_name = "course/profile.html"


class InstanceView(EnrollableViewMixin, BaseTemplateView):
    template_name = "course/toc.html"


class Enroll(EnrollableViewMixin, BaseRedirectView):

    def post(self, request, *args, **kwargs):
        self.handle()

        if self.enrolled or not self.enrollable:
            messages.error(self.request, _("You cannot enroll, or have already enrolled, to this course."))
            raise PermissionDenied()

        # Support enrollment questionnaires.
        exercise = LearningObject.objects.find_enrollment_exercise(self.instance)
        if exercise:
            return self.redirect(exercise.get_absolute_url())

        self.instance.enroll_student(self.request.user)
        return self.redirect(self.instance.get_absolute_url())


class ModuleView(CourseModuleBaseView):
    template_name = "course/module.html"

    def get(self, request, *args, **kwargs):
        self.handle()
        if not self.module.is_after_open():
            messages.warning(self.request,
                _("The course module is not yet open for students."))
        return super().get(request, *args, **kwargs)


class CalendarExport(CourseInstanceMixin, View):

    def get(self, request, *args, **kwargs):
        self.handle()

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


# class FilterCategories(CourseInstanceMixin, BaseRedirectView):
#
#     def post(self, request, *args, **kwargs):
#         self.handle()
#
#         if "category_filters" in request.POST:
#             visible_category_ids = [int(cat_id)
#                 for cat_id in request.POST.getlist("category_filters")]
#             for category in self.instance.categories.all():
#                 if category.id in visible_category_ids:
#                     category.set_hidden_to(self.profile, False)
#                 else:
#                     category.set_hidden_to(self.profile, True)
#         else:
#             messages.warning(request,
#                 _("You tried to hide all categories. "
#                   "Select at least one visible category."))
#
#         return self.redirect_kwarg("next", backup=self.instance)
