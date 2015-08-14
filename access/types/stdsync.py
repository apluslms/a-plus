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
    @type user: C{str}
    @param user: None or a user id to direct grading
    @rtype: C{django.http.response.HttpResponse}
    @return: a response    

'''
from util.templates import render_configured_template
from access.config import ConfigError
from access.types.forms import GradedForm
from access.types.stdasync import _authHash, _aplusStudent


def noGrading(request, course, exercise, user):
    '''
    Presents a template and does no grading.
    
    '''
    return render_configured_template(request, course, exercise, None, None);


def comparePostValues(request, course, exercise, user):
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
            result = { "accepted": True, "received": received, "points": points, "failed": failed }
        else:
            result = { "accepted": True, "points": 0 }

    return render_configured_template(request, course, exercise, None, result)


def createForm(request, course, exercise, user):
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
        
        result = { "form": form, "accepted": True, "points": points, "error_groups": error_groups, "error_fields": error_fields }
    
    # Fix action URL for A+ feedback
    if request.method == "POST" and "post_url" in request.GET:
        result["fix_url"] = request.GET["post_url"]

    return render_configured_template(request, course, exercise, 'access/create_form_default.html', result)


def md5Authentication(request, course, exercise, user):
    '''
    Creates an md5 hash for user authentication.
    
    '''
    if user is None:
        user = _aplusStudent(request)
    return render_configured_template(request, course, exercise, None,
        { "user": user, "hash": _authHash(exercise["auth_secret"], user) })


def pointsInRange(points, max_points):
    '''
    Check the points is in range.
    
    '''
    if points > max_points:
        return max_points
    if points < 0:
        return 0
    return points
