import datetime

import icalendar
from django.conf import settings
from django.contrib import messages
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import View

from lib.remote_page import RemotePage, RemotePageException
from lib.viewbase import BaseRedirectView
from userprofile.viewbase import ACCESS, UserProfileView
from .viewbase import CourseBaseView, CourseInstanceBaseView, \
    CourseModuleBaseView, CourseChapterView, CourseInstanceMixin
from .models import CourseInstance


class HomeView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "course/index.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.welcome_text = settings.WELCOME_TEXT
        self.instances = CourseInstance.objects.get_active(self.request.user)
        self.note("welcome_text", "instances")


class ArchiveView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "course/archive.html"


class CourseView(CourseBaseView):
    template_name = "course/course.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.instances = self.course.instances.get_active(self.request.user)
        self.note("instances")


class InstanceView(CourseInstanceBaseView):
    template_name = "course/toc.html"


class ProfileView(CourseInstanceBaseView):
    template_name = "course/profile.html"


class ModuleView(CourseModuleBaseView):
    template_name = "course/module.html"

    def get(self, request, *args, **kwargs):
        self.handle()
        if not self.module.is_after_open():
            messages.warning(self.request,
                _("The course module is not yet open for students."))
        return self.response()


class ChapterView(CourseChapterView):
    template_name = "course/chapter.html"

    def get(self, request, *args, **kwargs):
        self.handle()
        if not self.module.is_after_open():
            messages.warning(self.request,
                _("The course module is not yet open for students."))
        try:
            page = RemotePage(self.chapter.content_url)
            page.fix_relative_urls()
            content = page.element_or_body("chapter")
        except RemotePageException:
            messages.error(self.request,
                _("Connecting to the content service failed!"))
            content = None
        return self.response(content=content)


class CalendarExport(CourseInstanceMixin, View):

    def get(self, request, *args, **kwargs):
        self.handle()

        cal = icalendar.Calendar()
        cal.add('prodid', '-// A+ calendar //')
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


class FilterCategories(CourseInstanceMixin, BaseRedirectView):

    def post(self, request, *args, **kwargs):
        self.handle()

        if "category_filters" in request.POST:
            visible_category_ids = [int(cat_id)
                for cat_id in request.POST.getlist("category_filters")]
            for category in self.instance.categories.all():
                if category.id in visible_category_ids:
                    category.set_hidden_to(self.profile, False)
                else:
                    category.set_hidden_to(self.profile, True)
        else:
            messages.warning(request,
                _("You tried to hide all categories. "
                  "Select at least one visible category."))

        return self.redirect_kwarg("next", backup=self.instance)
