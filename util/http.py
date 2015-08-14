'''
Utility functions for exercise HTTP responses.

'''
from util.templates import template_to_str
import urllib, urllib2
import json
import logging

LOGGER = logging.getLogger('main')


def get_json(url):
    '''
    Gets URL response content.
    
    @type url: C{str}
    @param url: an URL to get
    @rtype: C{str}
    @return: the HTTP response content
    '''
    return json.load(urllib2.urlopen(url, timeout=3))


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
    html = template_to_str(course, exercise, template, result)

    # Make unicode results ascii.
    if isinstance(html, unicode):
        html = html.encode("ascii", "xmlcharrefreplace")

    data = {
        "max_points": max(result.get("max_points", exercise.get("max_points", 0)), 1),
        "points": result.get("points", 0),
        "feedback": html
    }

    if "error" in result and result["error"]:
        data["error"] = True

    # Try to send send the result.
    res = None
    try:
        response = urllib2.urlopen(submission_url, urllib.urlencode(data))
        try:
            res = json.loads(response.read())
        except Exception:
            pass
        if not res or not "success" in res or not res["success"]:
            LOGGER.error("Result POST to \"%s\" got unexpected response: %s", submission_url, res)
    except ValueError:
        LOGGER.error("Invalid submission_url \"%s\"", submission_url)


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
    post_result(submission_url, course, exercise, "access/task_system_error.html",
                { "error": True })
