
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
from userprofile.models import UserProfile
from exercise.presentation.summary import UserModuleSummary


def home(request):
    """
    Lists active courses for A+ home page.
    """
    context = RequestContext(request, {
        "welcome_text": settings.WELCOME_TEXT,
        "instances": CourseInstance.objects.get_active(request.user)
    })
    return render_to_response("course/index.html", context)


def course_archive(request):
    """
    Uses AJAX and API to produce a list of all courses.
    """
    context = RequestContext(request)
    return render_to_response("course/archive.html", context)


@access_resource
def view_course(request, course_url=None, course=None):
    """
    Lists course instances for a course.
    """
    instances = course.instances.get_active(request.user)
    context = CourseContext(request, course=course, instances=instances)
    return render_to_response("course/course.html", context)


@access_resource
def view_instance(request, course_url=None, instance_url=None,
                  course=None, course_instance=None):
    """
    Creates a course instance main view.
    """
    # TODO: check if course has content modules for a content index
    return redirect('user_score',
                    course_url=course.url,
                    instance_url=course_instance.url)


@access_resource
def view_module(request, course_url=None, instance_url=None, module_url=None,
                course=None, course_instance=None, module=None):
    """
    Displays module content if such exists and receives exercise submissions.
    
    """
    if module.content_url == "":
        return redirect('user_score',
                        course_url=course.url,
                        instance_url=course_instance.url)
    
    # TODO: fetch and cache from content_url, handle exercise submissions
    
    summary = UserModuleSummary(module, request.user)
    return render_to_response("exercise/module.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        module=module,
        module_summary=summary,
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
