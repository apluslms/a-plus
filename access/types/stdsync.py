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
from django.core.exceptions import PermissionDenied

from util.cache import InProcessCache
from util.http import not_modified_since, not_modified_response, cache_headers
from util.templates import render_configured_template, render_template
from .forms import GradedForm
from .auth import make_hash, get_uid
from ..config import ConfigError


# Hold on to nonces for some time.
nonces = InProcessCache(limit=100)


def acceptNonce(request):
    '''
    Post containing unique _nonce is only accepted once.
    '''
    if request.method == 'POST':
        if '_nonce' in request.POST:
            nonce = str(request.POST['_nonce'])
            if nonce in nonces:
                raise PermissionDenied('Repeating nonce')
            nonces[nonce] = True
            return True
        return False


def noGrading(request, course, exercise, post_url):
    '''
    Presents a template and does no grading.
    '''
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)
    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url, None, None
        ),
        request,
        exercise
    )


def comparePostValues(request, course, exercise, post_url):
    '''
    Presents a template and grades configured POST values.
    '''
    if "max_points" not in exercise:
        raise ConfigError("Missing required \"max_points\" in exercise configuration")

    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    result = None
    if request.method == "POST":

        if "values" in exercise:
            received = {}
            points = 0
            failed = []

            # Check each POST value against the rule.
            for (name, rule) in exercise["values"].items():
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

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url, None, result
        ),
        request,
        exercise
    )


def createForm(request, course, exercise, post_url):
    '''
    Creates form by configuration and grades answers.
    '''
    if "max_points" not in exercise:
        raise ConfigError("Missing required \"max_points\" in exercise configuration")
    try:
        acceptNonce(request)
    except PermissionDenied:
        return render_template(request, course, exercise, post_url,
            'access/exercise_frame.html', { "error":True, "nonce_used":True })

    last = False
    if request.method == 'POST':
        try:
            n = int(request.GET.get('ordinal_number', '0'))
            max_n = int(request.GET.get('max_submissions', '0'))
        except ValueError:
            pass
        last = max_n > 0 and n >= max_n

    form = GradedForm(request.POST or None, request.FILES or None,
        exercise=exercise, show_correct_once=last)

    # Support caching of non personalized forms.
    if not form.randomized and not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    result = { "form": form }

    # Grade valid form posts.
    if form.is_valid():
        (points, error_groups, error_fields) = form.grade()
        points = pointsInRange(points, exercise["max_points"])

        # Allow passing to asynchronous grading.
        if "actions" in exercise:
            from .stdasync import _saveForm
            return _saveForm(request, course, exercise, post_url, form)

        # If points are not granted by form fields.
        if points == 0 and not error_fields:
            points = exercise["max_points"]

        result = { "form": form, "accepted": True, "points": points,
            "error_groups": error_groups, "error_fields": error_fields }

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            'access/create_form_default.html', result
        ),
        request,
        exercise,
        form.randomized,
    )


def createFormModel(request, course, exercise, parameter):
    form = GradedForm(None, exercise=exercise, show_correct=True)
    form.bind_initial()
    points,error_groups,error_fields = form.grade()
    result = { "form": form, "accepted": True, "points": points,
        "error_groups": error_groups, "error_fields": error_fields }
    return render_template(request, course, exercise, None,
        'access/graded_form.html', result)


def md5Authentication(request, course, exercise, post_url):
    '''
    Creates an md5 hash for user authentication.
    '''
    user = get_uid(request)
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
