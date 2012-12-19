# Python
from icalendar import Calendar, Event

# Django
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse, HttpResponseForbidden
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.template import loader
from django.utils.translation import ugettext_lazy as _

# A+
from course.models import Course, CourseInstance
from course.context import CourseContext
from course.results import ResultTable
from course.forms import CourseModuleForm
from exercise.exercise_summary import CourseSummary
from exercise.submission_models import Submission
from exercise.exercise_models import CourseModule

def _get_course_instance(course_url, instance_url):
    '''
    Returns a CourseInstance or raises an HttpResponse with code 404 (not found) based on the 
    given course URL and instance URL.
    
    @param course_url: the URL attribute of a course
    @param instance_url: the URL attribute of an instance belonging to the course
    @return: a CourseInstance model matching the attributes
    '''
    return get_object_or_404(CourseInstance, url=instance_url, course__url=course_url)

def course_archive(request):
    """ 
    Displays a course archive of all courses in the system.
    """
    
    context = CourseContext(request)
    return render_to_response("course/archive.html", context)

@login_required
def view_course(request, course_url):
    """ 
    Displays a page for the given course. The page consists of a list of
    course instances for the course. 
    
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    """
    
    course      = get_object_or_404(Course, url=course_url)
    instances = course.get_visible_open_instances(request.user.get_profile())

    context = CourseContext(request, course=course, instances=instances)
    return render_to_response("course/view.html", context)

@login_required
def view_instance(request, course_url, instance_url):
    """ Renders a dashboard page for a course instance. A dashboard has a list
        of exercise rounds and exercises and plugins that may have been 
        installed on the course. Students also see a summary of their progress
        on the course dashboard.
        
        @param request: the Django HttpRequest object
        @param course_url: the url value of a Course object
        @param instance_url: the url value of a CourseInstance object """
    
    course_instance = _get_course_instance(course_url, instance_url)

    if not course_instance.is_visible_to(request.user.get_profile()):
        return HttpResponseForbidden("You are not allowed to access this view.")

    course_summary  = CourseSummary(course_instance, request.user)
    course_instance.plugins.all()
    
    return render_to_response("course/view_instance.html", 
                              CourseContext(request, 
                                            course_instance=course_instance, 
                                            course_summary=course_summary
                                            ))


@login_required
def view_my_page(request, course_url, instance_url):
    """ 
    Renders a personalized page for a student on the course. The page is intended to show 
    how well the student is doing on the course and shortcuts to the latest submissions.
    
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    @param instance_url: the url value of a CourseInstance object 
    """
    
    course_instance = _get_course_instance(course_url, instance_url)

    if not course_instance.is_visible_to(request.user.get_profile()):
        return HttpResponseForbidden("You are not allowed to access this view.")

    course_summary  = CourseSummary(course_instance, request.user)
    submissions     = request.user.get_profile().submissions.filter(exercise__course_module__course_instance=course_instance).order_by("-id")
    
    return render_to_response("course/view_my_page.html", 
                              CourseContext(request, 
                                            course_instance=course_instance,
                                            course_summary=course_summary,
                                            submissions=submissions
                                            ))


def view_instance_calendar(request, course_url, instance_url):
    """ 
    Renders a iCalendar feed for a CourseInstance. Unlike most other views in this module, this
    view does not require the user to be logged in.
    
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    @param instance_url: the url value of a CourseInstance object 
    """
    
    course_instance = _get_course_instance(course_url, instance_url)

    if not course_instance.is_visible_to(request.user.get_profile()):
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    cal = Calendar()
    
    cal.add('prodid', '-// A+ calendar //')
    cal.add('version', '2.0')
    
    for course_module in course_instance.course_modules.all():
        event = Event()
        event.add('summary', course_module.name)
        
        # FIXME: Currently all times added are the closing time.
        # The event will need to be longer than 0 seconds in order 
        # to be displayed clearly on calendar applications.
        event.add('dtstart', course_module.closing_time)
        event.add('dtend', course_module.closing_time)
        event.add('dtstamp', course_module.closing_time)
        
        event['uid'] = "module/" + str(course_module.id) + "/A+"
        
        cal.add_component(event)
    
    response = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
    return response


@login_required
def view_instance_results(request, course_url, instance_url):
    """ 
    Renders a results page for a course instance. The results contain individual
    scores for each student on each exercise.
    
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    @param instance_url: the url value of a CourseInstance object 
    """
    
    course_instance = _get_course_instance(course_url, instance_url)

    if not course_instance.is_visible_to(request.user.get_profile()):
        return HttpResponseForbidden("You are not allowed to access this view.")

    table           = ResultTable(course_instance)
    
    table_html = loader.render_to_string("course/_results_table.html", {"result_table": table})
    
    return render_to_response("course/view_results.html", 
                              CourseContext(request, course_instance=course_instance,
                                                     result_table=table,
                                                     table_html=table_html
                                             ))


@login_required
def teachers_view(request, course_url, instance_url):
    """ 
    This is the special page for teachers of the course instance.
    
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    @param instance_url: the url value of a CourseInstance object 
    """
    course_instance = _get_course_instance(course_url, instance_url)
    has_permission  = course_instance.is_teacher(request.user.get_profile()) 
    
    if not has_permission:
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    return render_to_response("course/teachers_view.html", 
                              CourseContext(request, course_instance=course_instance)
                              )


@login_required
def assistants_view(request, course_url, instance_url):
    """ 
    This is the special page for the assistants on the given course instance.
    
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    @param instance_url: the url value of a CourseInstance object 
    """
    course_instance = _get_course_instance(course_url, instance_url)
    
    has_permission  = course_instance.is_staff(request.user.get_profile()) 
    if not has_permission:
        return HttpResponseForbidden(_("You are not allowed to access this view."))
    
    return render_to_response("course/assistants_view.html", 
                              CourseContext(request, course_instance=course_instance)
                              )


@login_required
def add_or_edit_module(request, course_url, instance_url, module_id=None):
    """ 
    This page can be used by teachers to add new modules and edit existing ones.
    
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    @param instance_url: the url value of a CourseInstance object
    @param module_id: The id of the module to edit. If not given, a new module is created. 
    """
    course_instance = _get_course_instance(course_url, instance_url)
    has_permission  = course_instance.is_teacher(request.user.get_profile()) 
    
    if not has_permission:
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    if module_id != None:
        module = get_object_or_404(CourseModule, id=module_id, course_instance=course_instance)
    else:
        module = CourseModule(course_instance=course_instance)
    
    if request.method == "POST":
        form = CourseModuleForm(request.POST)
        if form.is_valid():
            module = form.save()
            messages.success(request, _('The course module was saved successfully.'))
    else:
        form = CourseModuleForm(instance=module)
    
    return render_to_response("course/edit_module.html", 
                              CourseContext(request, course_instance=course_instance,
                                                     module=module,
                                                     form=form
                                             ))
