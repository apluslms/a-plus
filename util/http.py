'''
Utility functions for exercise HTTP responses.

'''
import requests
import logging
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

    # Try to send send the result.
    try:
        r = requests.post(submission_url, data=data)
        if r.status_code != 200:
            r.raise_for_status()
        rsp = r.json()
        if not "success" in rsp or not rsp["success"]:
            LOGGER.error("Result POST to \"%s\" got unexpected response: %s",
                submission_url, rsp.body)
    except Exception:
        LOGGER.error("Failed to submit \"%s\"", submission_url)


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
