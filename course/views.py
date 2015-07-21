import datetime

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.http.response import HttpResponse, HttpResponseForbidden
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _
from icalendar import Calendar, Event

from course.context import CourseContext
from course.decorators import access_resource
from course.models import CourseInstance
from lib.remote_page import RemotePage, RemotePageException
from userprofile.models import UserProfile


def home(request):
    """
    Lists active courses for A+ home page.
    """
    return render_to_response("course/index.html", RequestContext(
        request, {
            "welcome_text": settings.WELCOME_TEXT,
            "instances": CourseInstance.objects.get_active(request.user)
        }
    ))


def course_archive(request):
    """
    Uses AJAX and API to produce a list of all courses.
    """
    return render_to_response("course/archive.html", RequestContext(request))


@access_resource
def view_course(request, course_url=None, course=None):
    """
    Lists course instances for a course.
    """
    return render_to_response("course/course.html", CourseContext(
        request,
        course=course,
        instances=course.instances.get_active(request.user)
    ))


@access_resource
def view_instance(request, course_url=None, instance_url=None,
                  course=None, course_instance=None):
    if course_instance.has_chapters():
        return render_to_response("course/toc.html", CourseContext(
            request,
            course=course,
            course_instance=course_instance
        ))
    import exercise.views
    return exercise.views.user_score(
        request, course_url=course_url, instance_url=instance_url)


@access_resource
def view_module(request, course_url=None, instance_url=None, module_url=None,
                course=None, course_instance=None, module=None):
    return HttpResponse("TODO")


@access_resource
def view_chapter(request, course_url=None, instance_url=None, module_url=None,
                chapter_url=None,
                course=None, course_instance=None, module=None,
                chapter=None):
    try:
        page = RemotePage(chapter.content_url)
        page.fix_relative_urls()
    except RemotePageException:
        messages.error(request, _("Connecting to the content service failed!"))
    return render_to_response("course/chapter.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        module=module,
        chapter=chapter,
        content=page.element_or_body("chapter"),
    ))


@access_resource
def export_calendar(request, course_url=None, instance_url=None,
                           course=None, course_instance=None):
    """
    Renders a iCalendar feed for a CourseInstance. Unlike most other views in this module, this
    view does not require the user to be logged in.
    """
    cal = Calendar()
    cal.add('prodid', '-// A+ calendar //')
    cal.add('version', '2.0')

    for course_module in course_instance.course_modules.all():
        event = Event()
        event.add('summary', course_module.name)

        event.add('dtstart', course_module.closing_time - datetime.timedelta(hours=1))
        event.add('dtend', course_module.closing_time)
        event.add('dtstamp', course_module.closing_time)

        event['uid'] = "module/" + str(course_module.id) + "/A+"

        cal.add_component(event)

    response = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
    return response


@access_resource
def filter_categories(request, course_url=None, instance_url=None,
                      course=None, course_instance=None):
    """
    Filters the visible learning object categories for the current user.
    """
    if request.method != "POST":
        return HttpResponseForbidden(_("This view should only be accessed with HTTP POST."))

    profile = UserProfile.get_by_request(request)

    if "category_filters" in request.POST:
        visible_category_ids = [int(cat_id) for cat_id
                                in request.POST.getlist("category_filters")]

        for category in course_instance.categories.all():
            if category.id in visible_category_ids:
                category.set_hidden_to(profile, False)
            else:
                category.set_hidden_to(profile, True)
    else:
        messages.warning(request,
            _("You tried to hide all categories. Select at least one visible category."))

    if "next" in request.GET:
        next_url = request.GET["next"]
    else:
        next_url = course_instance.get_absolute_url()
    return HttpResponseRedirect(next_url)
