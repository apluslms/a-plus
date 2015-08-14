from django.shortcuts import render, redirect
from django.http.response import HttpResponse, Http404
from django.utils.module_loading import import_by_path
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from access.config import ConfigParser, ConfigError
from grader.tasks import queue_length as qlength
import os
import json
import logging

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
        return _json_response(request, { "ready": True, "courses": _filter_fields(courses, ["key", "name"]) })
    
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
        return _json_response(request, { "ready": True,
                                         "course_name": course["name"],
                                         "exercises": _filter_fields(exercises, ["key", "title"]) })
    
    return render(request, 'access/course.html', { 'course': course, 'exercises': exercises })


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
    # Fetch the language and user parameters if given.
    lang = request.REQUEST.get('lang', None)
    user = request.REQUEST.get('user', None)
    
    # Fetch the corresponding exercise entry from the config.
    (course, exercise) = config.exercise_entry(course_key, exercise_key, lang=lang)
    if course is None or exercise is None:
        raise Http404()
    
    # Try to call the configured view.
    exview = None
    try:
        exview = import_by_path(exercise["view_type"])
    except ImproperlyConfigured as e:
        raise ConfigError("Invalid \"view_type\" in exercise configuration.", e)
    return exview(request, course, exercise, user)


def pull_request(request):
    '''
    Records a pull request to update course exercises from version repository.
    
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
                os.chmod(flagdir, 0777)
            filename = os.path.join(flagdir, "gitpull.flag")
            with open(filename, "a") as f:
                f.write("%s\n" % (course["key"]))
            status["updated"] = True
        else:
            status["not_found"] = True
        return redirect('access.views.pull_request')
    
    log = ""
    filename = os.path.join(settings.BASE_DIR, "gitpull.log")
    if os.path.exists(filename):
        with open(filename, "r") as f:
            log = f.read()
    
    return render(request, 'access/pull_request.html', { "courses": courses,
                                                         "status": status, "log": log })


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
    return _json_response(request, { "success": True })


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
    

def _json_response(request, data):
    '''
    Returns a JSON response.
    
    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type data: C{dict}
    @param data: data for the response
    @rtype: C{django.http.response.HttpResponse}
    @return: a JSON response
    '''
    return HttpResponse(json.dumps(data), content_type="application/json")
