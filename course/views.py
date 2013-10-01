# Python
from collections import defaultdict
from icalendar import Calendar, Event

# Django
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse, HttpResponseForbidden, \
    HttpResponseRedirect
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.template import loader
from django.utils.translation import ugettext_lazy as _

# A+
from apps.app_renderers import build_plugin_renderers
from course.models import Course, CourseInstance
from course.context import CourseContext
from course.results import ResultTable
from course.forms import CourseModuleForm
from exercise.exercise_summary import UserCourseSummary
from exercise.submission_models import Submission
from exercise.exercise_models import CourseModule, BaseExercise,\
    LearningObjectCategory, LearningObject

# TODO: The string constant "You are not allowed to access this view." is
# repeated a lot in this file. Giving this error message should be somehow
# unified.

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
    """
    Renders the home page for a course instance showing the current student's
    progress on the course.

    On the page, all the exercises of the course instance are organized as a
    schedule. They are primarily organized in a list of course modules which
    are primarily ordered according to their closing times and secondarily to
    their opening times. Inside the course modules the exercises are ordered
    according to their order attribute but in the same time, they are also
    grouped to their categories.

    The home page also contains a summary of the student's progress for the
    whole course instance, course modules, categories and each exercise.
        
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    @param instance_url: the url value of a CourseInstance object
    """
    
    course_instance = _get_course_instance(course_url, instance_url)
    user_profile = request.user.get_profile()

    if not course_instance.is_visible_to(user_profile):
        return HttpResponseForbidden("You are not allowed "
                                     "to access this view.")

    # In the following code, we are going to construct a special data structure
    # to be used in the view_instance.html. We refer to the structure as the
    # exercise_tree. The main idea is to provide all the data for the template
    # in a way that makes the template as simple as possible.
    #
    # This is how the structure should be used in the template:
    #
    #   {% for course_module, round_summary, uncategorized_exercise_level, category_level in exercise_tree %}
    #
    #       ...
    #
    #       {% for exercise, exercise_summary in uncategorized_exercise_level %}
    #           ...
    #       {% endfor %}
    #
    #       ...
    #
    #       {% for category, category_summary, categorized_exercise_level in category_level %}
    #
    #           ...
    #
    #           {% for exercise, exercise_summary in categorized_exercise_level %}
    #               ...
    #           {% endfor %}
    #
    #           ...
    #
    #       {% endfor %}
    #
    #       ...
    #
    #   {% endfor %}
    #
    # Notice that all the nodes of the tree are tuples (all the lists contain
    # tuples). The tuples are of course formatted the same way in a particular
    # tree level (list).
    #
    # The CourseModule objects are ordered chronologically. The exercises are
    # ordered by their order attribute. The order of the categories is
    # determined by the order of the exercises. For example, if the first two
    # exercises belong to category A and then the following two exercises
    # belong to category B, our list of categories will begin like [A, B, ...].
    # Note that the category A may be in the list later too if there is more
    # exercises that belong to the category A. For example, if the fifth
    # exercises would belong to category A, our list of categories would be
    # [A, B, A, ...].
    #
    # The view_instance.html template renders the CourseModules objects so that
    # in addition to the categorized exercise list, there is an additional
    # small list of hotlinks for the exercises. For this reason, the exercise
    # tree separates to two different list on the second level--the list
    # containing all the exercises of the CourseModule (for the hotlinks) and
    # the list containing the LearningObjectCategory objects. The latter of
    # these then has a third level which finally contains lists of exercises
    # (grouped by the LearningObjectCategory objects of their parent node that
    # is).
    #
    # Also notice the summaries in the tuples. Those alway correspond to the
    # main object of the tuple.
    #

    course_summary = UserCourseSummary(course_instance, request.user)

    visible_categories = LearningObjectCategory.objects.filter(
        course_instance=course_instance).exclude(hidden_to=user_profile)
    visible_exercises = (BaseExercise.objects.filter(
        course_module__course_instance=course_instance,
        category__in=visible_categories)
        .select_related("course_module", "category").order_by("order"))

    visible_exercises_by_course_modules = defaultdict(list)
    for exercise in visible_exercises:
        (visible_exercises_by_course_modules[exercise.course_module]
         .append(exercise))

    visible_exercises_by_course_modules = sorted(
        visible_exercises_by_course_modules.items(),
        key=lambda t: (t[0].closing_time, t[0].opening_time))

    exercise_tree = [
        (course_module,
         course_summary.get_exercise_round_summary(course_module),
         [(exercise, course_summary.get_exercise_summary(exercise))
          for exercise in exercises], [])
        for course_module, exercises in visible_exercises_by_course_modules]

    for course_module, round_summary, exercises_and_summaries,\
            exercise_tree_category_level in exercise_tree:
        for exercise, exercise_summary in exercises_and_summaries:
            if (len(exercise_tree_category_level) == 0
                    or exercise_tree_category_level[-1][0]
                    != exercise.category):
                exercise_tree_category_level.append(
                    (exercise.category,
                     course_summary.get_exercise_round_summary(
                         exercise.category),
                     []))
            exercise_tree_category_level[-1][2].append((exercise,
                                                        exercise_summary))

    # Finished constructing the exercise_tree.

    course_instance_max_points = BaseExercise.get_course_instance_max_points(
        course_instance)

    plugin_renderers = build_plugin_renderers(
        plugins=course_instance.plugins.all(),
        view_name="course_instance",
        user_profile=user_profile,
        course_instance=course_instance)
    
    return render_to_response("course/view_instance.html", 
                              CourseContext(request, 
                                            course_instance=course_instance, 
                                            course_summary=course_summary,
                                            plugin_renderers=plugin_renderers,
                                            exercise_tree=exercise_tree,
                                            course_instance_max_points=
                                            course_instance_max_points,
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
        return HttpResponseForbidden("You are not allowed "
                                     "to access this view.")

    course_summary  = UserCourseSummary(course_instance, request.user)
    submissions     = request.user.get_profile().submissions.filter(exercise__course_module__course_instance=course_instance).order_by("-id")

    course_instance_max_points = BaseExercise.get_course_instance_max_points(
        course_instance)
    
    return render_to_response("course/view_my_page.html", 
                              CourseContext(request, 
                                            course_instance=course_instance,
                                            course_summary=course_summary,
                                            submissions=submissions,
                                            course_instance_max_points=
                                            course_instance_max_points,
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

    if request.user.is_authenticated():
        profile = request.user.get_profile()
    else:
        profile = None

    if not course_instance.is_visible_to(profile):
        return HttpResponseForbidden("You are not allowed "
                                     "to access this view.")
    
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
        return HttpResponseForbidden("You are not allowed "
                                     "to access this view.")

    table           = ResultTable(course_instance)
    
    table_html = loader.render_to_string("course/_results_table.html", {"result_table": table})
    
    return render_to_response("course/view_results.html", 
                              CourseContext(request, course_instance=course_instance,
                                                     result_table=table,
                                                     table_html=table_html
                                             ))


@login_required
def set_schedule_filters(request, course_url, instance_url):
    if request.method != "POST":
        return HttpResponseForbidden(_("This view should only be accessed "
                                       "with HTTP POST."))

    course_instance = _get_course_instance(course_url, instance_url)
    profile = request.user.get_profile()

    if not request.POST.has_key("category_filters"):
        return HttpResponseForbidden("You are trying to hide all categories. "
                                     "Select at least one category to be "
                                     "visible!")

    visible_category_ids = [int(cat_id) for cat_id
                            in request.POST.getlist("category_filters")]

    for category in course_instance.categories.all():
        if category.id in visible_category_ids:
            category.set_hidden_to(profile, False)
        else:
            category.set_hidden_to(profile, True)


    if request.GET.has_key("next"):
        next = request.GET["next"]
    else:
        next = course_instance.get_absolute_url()

    return HttpResponseRedirect(next)


@login_required
def teachers_view(request, course_url, instance_url):
    """ 
    This is the special page for teachers of the course instance.
    
    @param request: the Django HttpRequest object
    @param course_url: the url value of a Course object
    @param instance_url: the url value of a CourseInstance object 
    """
    course_instance = _get_course_instance(course_url, instance_url)
    has_permission  = (course_instance.is_teacher(request.user.get_profile())
            or request.user.is_superuser
            or request.user.is_staff)
    
    if not has_permission:
        return HttpResponseForbidden("You are not allowed "
                                     "to access this view.")
    
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
        return HttpResponseForbidden(_("You are not allowed "
                                       "to access this view."))
    
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
        return HttpResponseForbidden("You are not allowed "
                                     "to access this view.")
    
    if module_id != None:
        module = get_object_or_404(CourseModule, id=module_id, course_instance=course_instance)
    else:
        module = CourseModule(course_instance=course_instance)
    
    if request.method == "POST":
        form = CourseModuleForm(request.POST)
        if form.is_valid():
            module = CourseModuleForm(request.POST, instance=module)
            module.save()
            messages.success(request, _('The course module was saved successfully.'))
    else:
        form = CourseModuleForm(instance=module)
    
    return render_to_response("course/edit_module.html", 
                              CourseContext(request, course_instance=course_instance,
                                                     module=module,
                                                     form=form
                                             ))
