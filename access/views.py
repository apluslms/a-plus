from django.shortcuts import render
from django.http.response import HttpResponse, JsonResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from django.utils import translation
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.conf import settings
import copy
import os
import json

from access.config import config
from util.files import read_and_remove_submission_meta, clean_submission_dir
from util.queue import queue_length as qlength
from util.http import post_result
from util.importer import import_named
from util.personalized import read_generated_exercise_file
from util import export


def index(request):
    '''
    Signals that the grader is ready and lists available courses.
    '''
    courses = config.courses()
    if request.is_ajax():
        return JsonResponse({
            "ready": True,
            "courses": _filter_fields(courses, ["key", "name"])
        })
    return render(request, 'access/ready.html', {
        "courses": courses,
        "manager": 'gitmanager' in settings.INSTALLED_APPS,
    })


def course(request, course_key):
    '''
    Signals that the course is ready to be graded and lists available exercises.
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
            'aplus-json', args=[course['key']])),
    })


def exercise(request, course_key, exercise_key):
    '''
    Presents the exercise and accepts answers to it.
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
    return import_named(course, exercise['view_type'])(
        request, course, exercise, post_url)


def exercise_ajax(request, course_key, exercise_key):
    '''
    Receives an AJAX request for an exercise.
    '''
    (course, exercise) = config.exercise_entry(course_key, exercise_key)
    if course is None or exercise is None or 'ajax_type' not in exercise:
        raise Http404()
    # jQuery does not send "requested with" on cross domain requests
    #if not request.is_ajax():
    #    return HttpResponse('Method not allowed', status=405)

    response = import_named(course, exercise['ajax_type'])(
        request, course, exercise)

    # No need to control domain as valid submission_url is required to submit.
    response['Access-Control-Allow-Origin'] = '*'
    return response


def exercise_model(request, course_key, exercise_key, parameter=None):
    '''
    Presents a model answer for an exercise.
    '''
    (course, exercise) = config.exercise_entry(course_key, exercise_key)
    if course is None or exercise is None:
        raise Http404()
    response = None

    path = None
    if 'model_files' in exercise:
        def find_name(paths, name):
            models = [(path,path.split('/')[-1]) for path in paths]
            for path,name in models:
                if name == parameter:
                    return path
            return None
        path = find_name(exercise['model_files'], parameter)
    if path:
        with open(os.path.join(course['dir'], path)) as f:
            content = f.read()
        response = HttpResponse(content, content_type='text/plain')
    else:
        try:
            response = import_named(course, exercise['view_type'] + "Model")(
                request, course, exercise, parameter)
        except ImportError:
            pass
    if response:
        return response
    else:
        raise Http404()


def aplus_json(request, course_key):
    '''
    Delivers the configuration as JSON for A+.
    '''
    course = config.course_entry(course_key)
    if course is None:
        raise Http404()
    data = _copy_fields(course, ["name", "description", "lang", "contact",
        "assistants", "start", "end", "categories",
        "numerate_ignoring_modules"])

    def children_recursion(parent):
        if not "children" in parent:
            return []
        result = []
        for o in [o for o in parent["children"] if "key" in o]:
            of = _type_dict(o, course.get("exercise_types", {}))
            if "config" in of:
                _, exercise = config.exercise_entry(course["key"], str(of["key"]))
                of = export.exercise(request, course, exercise, of)
            elif "static_content" in of:
                of = export.chapter(request, course, of)
            of["children"] = children_recursion(o)
            result.append(of)
        return result

    modules = []
    if "modules" in course:
        for m in course["modules"]:
            mf = _type_dict(m, course.get("module_types", {}))
            mf["children"] = children_recursion(m)
            modules.append(mf)
    data["modules"] = modules

    if "gitmanager" in settings.INSTALLED_APPS:
        data["build_log_url"] = request.build_absolute_uri(reverse("build-log-json", args=(course_key, )))
    return JsonResponse(data)


def queue_length(request):
    '''
    Reports the current queue length.
    '''
    return HttpResponse(qlength())


def test_result(request):
    '''
    Accepts and displays a result from a test submission.
    '''
    file_path = os.path.join(settings.SUBMISSION_PATH, 'test-result')

    if request.method == 'POST':
        vals = request.POST.copy()
        vals['time'] = str(timezone.now())
        with open(file_path, 'w') as f:
            f.write(json.dumps(vals))
        return JsonResponse({ "success": True })

    result = None
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            result = f.read()
    return HttpResponse(result or 'No test result received yet.')


def generated_exercise_file(request, course_key, exercise_key, exercise_instance, filename):
    '''
    Delivers a generated file of the exercise instance.
    '''
    # Fetch the corresponding exercise entry from the config.
    (course, exercise) = config.exercise_entry(course_key, exercise_key)
    if course is None or exercise is None:
        raise Http404()
    if "generated_files" in exercise:
        import magic
        for gen_file_conf in exercise["generated_files"]:
            if gen_file_conf["file"] == filename:
                if "allow_download" in gen_file_conf and gen_file_conf["allow_download"]:
                    file_content = read_generated_exercise_file(course, exercise,
                                                                exercise_instance, filename)
                    response = HttpResponse(file_content,
                                            content_type=magic.from_buffer(file_content, mime=True))
                    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
                    return response
                else:
                    # hide file existence with 404
                    raise Http404()
    raise Http404()

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


def container_post(request):
    '''
    Proxies the grading result from inside container to A+
    '''
    sid = request.POST.get('sid', None)
    if not sid:
        return HttpResponseForbidden("Missing sid")
    meta = read_and_remove_submission_meta(sid)
    clean_submission_dir(meta["dir"])

    course,exercise = config.exercise_entry(course_key, exercise_key, lang=meta["lang"])
    template = None
    if "feedback_template" in exercise:
        template = exercise["feedback_template"]
    else:
        template = "access/task_success.html"
    result = {
        # TODO
    }
    post_result(meta["url"], course, exercise, template, result)
