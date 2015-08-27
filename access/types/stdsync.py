'''
Views configurable for usual synchronous exercises that grade for
the immediate HTTP response. Synchronous strategy should only be
used where the work of queuing a task is greater than grading it.
Most of the exercises should be implemented asynchronously!

Functions take arguments:

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type post_url: C{str}
    @param post_url: the exercise post URL
    @rtype: C{django.http.response.HttpResponse}
    @return: a response

'''
from util.templates import render_configured_template
from .forms import GradedForm
from .auth import detect_user, make_hash
from ..config import ConfigError


def noGrading(request, course, exercise, post_url):
    '''
    Presents a template and does no grading.
    '''
    return render_configured_template(request, course, exercise, post_url, None, None);


def comparePostValues(request, course, exercise, post_url):
    '''
    Presents a template and grades configured POST values.
    '''
    result = None

    if "max_points" not in exercise:
        raise ConfigError("Missing required \"max_points\" in exercise configuration")

    if request.method == "POST":

        if "values" in exercise:
            received = {}
            points = 0
            failed = []

            # Check each POST value against the rule.
            for (name, rule) in exercise["values"].iteritems():
                received[name] = request.POST.get(name, False)
                if "accept" in rule:
                    if (received[name] in rule["accept"]) or \
                        (True in rule["accept"] and received[name] is not False):
                        if "points" in rule and isinstance(rule["points"], int):
                            points += rule["points"]
                    else:
                        failed.append(name)

            # If points are not granted by rules.
            if points == 0 and not failed:
                points = exercise["max_points"]

            points = pointsInRange(points, exercise["max_points"])
            result = { "accepted": True, "received": received,
                "points": points, "failed": failed }
        else:
            result = { "accepted": True, "points": 0 }

    return render_configured_template(request, course, exercise, post_url, None, result)


def createForm(request, course, exercise, post_url):
    '''
    Creates form by configuration and grades answers.
    '''
    if "max_points" not in exercise:
        raise ConfigError("Missing required \"max_points\" in exercise configuration")

    form = GradedForm(request.POST or None, exercise=exercise)
    result = { "form": form }

    # Grade valid form posts.
    if form.is_valid():
        (points, error_groups, error_fields) = form.grade()
        points = pointsInRange(points, exercise["max_points"])

        # If points are not granted by form fields.
        if points == 0 and not error_fields:
            points = exercise["max_points"]

        result = { "form": form, "accepted": True, "points": points,
            "error_groups": error_groups, "error_fields": error_fields }

    return render_configured_template(request, course, exercise, post_url,
        'access/create_form_default.html', result)


def md5Authentication(request, course, exercise, post_url):
    '''
    Creates an md5 hash for user authentication.
    '''
    user = detect_user(request)
    key = make_hash(exercise["auth_secret"], user)
    return render_configured_template(request, course, exercise, post_url,
        None, { "user": user, "hash": key })


def pointsInRange(points, max_points):
    '''
    Check the points is in range.
    '''
    if points > max_points:
        return max_points
    if points < 0:
        return 0
    return points
