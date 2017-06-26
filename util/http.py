'''
Utility functions for exercise HTTP responses.

'''
import logging
import requests
import time
import urllib
from django.conf import settings
from django.http import HttpResponseNotModified
from django.utils.http import http_date, parse_http_date_safe

from util.templates import template_to_str

LOGGER = logging.getLogger('main')


def get_json(url):
    '''
    Gets URL response content.

    @type url: C{str}
    @param url: an URL to get
    @rtype: C{str}
    @return: the HTTP response content
    '''
    r = requests.get(url, timeout=3)
    if r.status_code != 200:
        r.raise_for_status()
    return r.json()


def post_result(submission_url, course, exercise, template, result):
    '''
    Posts grading result to the submission URL.

    @type submission_url: C{str}
    @param submission_url: a submission URL where grader should POST result
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type template: C{str}
    @param template: a template name to use
    @type result: C{dict}
    @param result: additional results
    '''
    html = template_to_str(course, exercise, None, template, result)

    # Make unicode results ascii.
    html = html.encode("ascii", "xmlcharrefreplace")

    data = {
        "max_points": result.get("max_points", 1),
        "points": result.get("points", 0),
        "feedback": html
    }

    if "error" in result and result["error"]:
        data["error"] = True

    if "grading_data" in result:
        data["grading_data"] = result["grading_data"]

    post_data(submission_url, data)


def post_data(submission_url, data):
    try:
        r = requests.post(submission_url, data=data)
        if r.status_code != 200:
            r.raise_for_status()
        rsp = r.json()
        if not "success" in rsp or not rsp["success"]:
            LOGGER.error("Result POST to \"%s\" got unexpected response: %s",
                submission_url, rsp.body)
        else:
            return True
    except Exception:
        LOGGER.exception("Failed to submit \"%s\"", submission_url)
    return False


def post_system_error(submission_url, course=None, exercise=None):
    '''
    Posts report on detected system error to the submission URL.

    @type submission_url: C{str}
    @param submission_url: a submission URL where grader should POST result
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    '''
    post_result(submission_url, course, exercise,
        "access/task_system_error.html", { "error": True })


def update_url_params(url, params):
    delimiter = "&" if "?" in url else "?"
    return url + delimiter + urllib.parse.urlencode(params)


def cache_headers(response, request, exercise, flag=False):
    if (
        not flag
        and request.method == 'GET'
        and not exercise.get('personalized', False)
        and exercise.get('cacheable', True)
    ):
        response['Last-Modified'] = http_date(exercise['mtime'])
        expiry = exercise.get('expiry_minutes', settings.DEFAULT_EXPIRY_MINUTES)
        if expiry > 0:
            response['Expires'] = http_date(time.time() + expiry * 60)
    return response


def not_modified_since(request, exercise):
    if (
        request.method != 'GET'
        or exercise.get('personalized', False)
        or not exercise.get('cacheable', True)
    ):
        return False
    time = parse_http_date_safe(request.META.get('HTTP_IF_MODIFIED_SINCE'))
    return time and time >= exercise['mtime']


def not_modified_response(request, exercise):
    return cache_headers(HttpResponseNotModified(), request, exercise)
