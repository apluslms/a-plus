from django.shortcuts import render
from django.http.response import HttpResponse, JsonResponse, Http404
from django.utils import translation
from django.utils.module_loading import import_by_path
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.conf import settings
from access.config import ConfigParser, ConfigError
from grader.tasks import queue_length as qlength
import os
import logging
import copy


LOGGER = logging.getLogger('main')

# Hold on to the latest configuration for several requests.
config = ConfigParser()


def index(request):
    '''
    Signals that the grader is ready and lists available courses.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    courses = config.courses()
    if request.is_ajax():
        return JsonResponse({
            "ready": True,
            "courses": _filter_fields(courses, ["key", "name"])
        })
    return render(request, 'access/ready.html', { "courses": courses })


def course(request, course_key):
    '''
    Signals that the course is ready to be graded and lists available exercises.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course_key: C{str}
    @param course_key: a key of the course
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    (course, exercises) = config.exercises(course_key)
    if course is None:
        raise Http404()
    if request.is_ajax():
        return JsonResponse({
            "ready": True,
            "course_name": course["name"],
            "exercises": _filter_fields(exercises, ["key", "title"]),
        })
    return render(request, 'access/course.html', {
        'course': course,
        'exercises': exercises,
        'plus_config_url': request.build_absolute_uri(reverse(
            'access.views.aplus_json', args=[course['key']])),
    })


def exercise(request, course_key, exercise_key):
    '''
    Presents the exercise and accepts answers to it.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course_key: C{str}
    @param course_key: a key of the course
    @type exercise_key: C{str}
    @param exercise_key: a key of the exercise
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    post_url = request.GET.get('post_url', None)
    lang = request.GET.get('lang', None)

    # Fetch the corresponding exercise entry from the config.
    (course, exercise) = config.exercise_entry(course_key, exercise_key, lang=lang)
    if course is None or exercise is None:
        raise Http404()

    # Exercise language.
    if not lang:
        if "lang" in course:
            lang = course["lang"]
        else:
            lang = "en"
    translation.activate(lang)

    # Try to call the configured view.
    exview = None
    try:
        exview = import_by_path(exercise["view_type"])
    except ImproperlyConfigured as e:
        raise ConfigError("Invalid \"view_type\" in exercise configuration.", e)
    return exview(request, course, exercise, post_url)


def aplus_json(request, course_key):
    '''
    Delivers the configuration as JSON for A+.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course_key: C{str}
    @param course_key: a key of the course
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    course = config.course_entry(course_key)
    if course is None:
        raise Http404()
    data = _copy_fields(course, ["name", "description", "url_slug", "contact",
        "assistants", "start", "end", "categories"])
    data["modules"] = []
    if "modules" in course:
        for m in course["modules"]:
            mf = _type_dict(m, course.get("module_types", {}))

            # Build exercise configurations.
            efs = []
            if "exercises" in mf:
                for e in mf["exercises"]:
                    if "key" in e:
                        _, exercise = config.exercise_entry(course["key"], e["key"])
                        base = {
                            "title": exercise.get("title", ""),
                            "description": exercise.get("description", ""),
                            "url": request.build_absolute_uri(
                                reverse('access.views.exercise', args=[
                                    course["key"], exercise["key"]
                                ])),
                        }
                        base.update(e)
                        e = base
                    ef = _type_dict(e, course.get("exercise_types", {}))
                    efs.append(ef)
            mf["exercises"] = efs

            # Build chapter configurations.
            cfs = []
            if "chapters" in mf:
                for c in mf["chapters"]:
                    if "static_content" in c:
                        base = { "url": request.build_absolute_uri(
                            '%s%s/%s' % (
                                settings.STATIC_URL,
                                course["key"],
                                c["static_content"],
                            )),
                        }
                        base.update(c)
                        c = base
                    cfs.append(c)
            mf["chapters"] = cfs

            data["modules"].append(mf)
    return JsonResponse(data)


def pull_request(request):
    '''
    Records a pull request to update course exercises from version repository.
    TODO: Refactor into a specific app.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    courses = config.courses()
    status = {}

    if "key" in request.GET:
        course = config.course_entry(request.GET["key"])
        if course:
            import tempfile
            flagdir = os.path.join(tempfile.gettempdir(), "mooc-grader")
            if not os.path.exists(flagdir):
                os.makedirs(flagdir)
                os.chmod(flagdir, 0o777)
            filename = os.path.join(flagdir, "gitpull.flag")
            with open(filename, "a") as f:
                f.write("%s\n" % (course["key"]))
            status["updated"] = True
        else:
            status["not_found"] = True
    log = ""
    filename = os.path.join(settings.BASE_DIR, "gitpull.log")
    if os.path.exists(filename):
        with open(filename, "r") as f:
            log = f.read()

    return render(request, 'access/pull_request.html', {
        "courses": courses, "status": status, "log": log })


def queue_length(request):
    '''
    Reports the current queue length.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    return HttpResponse(qlength())


def null(request):
    '''
    Accepts any request and does nothing.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    if "error" in request.POST:
        LOGGER.warning("Received error result.")
    return JsonResponse({ "success": True })


def _filter_fields(dict_list, pick_fields):
    '''
    Filters picked fields from a list of dictionaries.

    @type dict_list: C{list}
    @param dict_list: a list of dictionaries
    @type pick_fields: C{list}
    @param pick_fields: a list of field names
    @rtype: C{list}
    @return: a list of filtered dictionaries
    '''
    result = []
    for entry in dict_list:
        new_entry = {}
        for name in pick_fields:
            new_entry[name] = entry[name]
        result.append(new_entry)
    return result


def _copy_fields(dict_item, pick_fields):
    '''
    Copies picked fields from a dictionary.

    @type dict_item: C{dict}
    @param dict_item: a dictionary
    @type pick_fields: C{list}
    @param pick_fields: a list of field names
    @rtype: C{dict}
    @return: a dictionary of picked fields
    '''
    result = {}
    for name in pick_fields:
        if name in dict_item:
            result[name] = copy.deepcopy(dict_item[name])
    return result

def _type_dict(dict_item, dict_types):
    '''
    Extends dictionary with a type reference.

    @type dict_item: C{dict}
    @param dict_item: a dictionary
    @type dict_types: C{dict}
    @param dict_types: a dictionary of type dictionaries
    @rtype: C{dict}
    @return: an extended dictionary
    '''
    base = {}
    if "type" in dict_item and dict_item["type"] in dict_types:
        base = copy.deepcopy(dict_types[dict_item["type"]])
    base.update(dict_item)
    if "type" in base:
        del base["type"]
    return base
