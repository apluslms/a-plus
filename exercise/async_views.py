"""
This module contains views for handling asynchronous exercise submissions 
through a submission URL.
"""
# Python
import socket
from urlparse import urlparse

# Django
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.utils import simplejson

# A+
from userprofile.models import UserProfile
from exercise.exercise_models import BaseExercise
from exercise.submission_models import Submission
from exercise.forms import SubmissionCallbackForm

def _get_service_ip(exercise_url):
    """
    This function takes a full URL as a parameter and returns the IP address of the host 
    as a string.
    """
    parse_result = urlparse(exercise_url)
    host = parse_result.netloc.split(":")[0]
    return socket.gethostbyname(host)


@csrf_exempt
def new_async_submission(request, student_ids, exercise_id, hash):
    """
    This view can be called to create new submissions for student(s). The view has a student and
    exercise specific URL, which can be authenticated by verifying the hash included in the URL.
    
    When the view is requested with a GET request, a JSON response with information about the
    exercise and previous submissions is included. When a POST request is made, the view tries
    to create a new submission for the given students. 
    
    @param request: a HttpRequest from Django
    @param student_ids: student ids for the UserProfile objects, separated by dashes (-)
    @param exercise_id: the id of the exercise object the submission is for
    @param hash: a hash that is constructed from a secret key, exercise id and student ids
    """
    
    exercise                = get_object_or_404(BaseExercise, id=exercise_id)
    user_ids                = student_ids.split("-")
    students                = UserProfile.objects.filter(id__in=user_ids)
    student_str, valid_hash = exercise.get_submission_parameters_for_students(students)
    
    # Check that all students were found with their user ids (the counts should match)
    # TODO: These validations could be more elegant
    assert len(students) == len(user_ids)
    assert hash == valid_hash
    assert student_str == student_ids
    
    return _async_submission_handler(request, exercise, students)

@csrf_exempt
def grade_async_submission(request, submission_id, hash):
    """
    This view can be called to grade a submissions asynchronously. The view has a submission
    specific URL, which can be authenticated by verifying the hash included in the URL.
    
    When the view is requested with a GET request, a JSON response with information about the
    exercise and previous submissions for the students is included. When a POST request is
    made, the view tries to add grading for the submission. 
    
    @param request: a HttpRequest from Django
    @param submission_id: id for the submission to grade
    @param hash: a hash that is random and must match the one saved for the submission
    """
    submission              = get_object_or_404(Submission, id=submission_id, hash=hash)
    exercise                = submission.exercise
    students                = submission.submitters.all()
    
    return _async_submission_handler(request, exercise, students, submission)

def _async_submission_handler(request, exercise, students, submission=None):
    """ 
    This function decides which function to call based on whether the request is made with 
    POST or GET method. For POST methods new submissions will be created or existing will be 
    graded, where as for GET requests information about the submission or exercise will be 
    returned.
    
    @param request: a HttpRequest from Django
    @param exercise: an BaseExercise object to which the submission is for
    @param students: the students (UserProfiles) as a QuerySet
    @param submission [optional]: the submission that is being created or updated
    """
    
    # Security check. Only the machine which hosts the exercise is allowed to accessthis view.
    if request.META["REMOTE_ADDR"] != _get_service_ip(exercise.service_url):
        return HttpResponseForbidden("Only the exercise service is allowed to access this URL.")
    
    if request.method == "GET":
        response_dict       = _get_async_submission_info(exercise, students)
    elif request.method == "POST":
        # Create a new submission if one is not provided
        if submission == None:
            submission      = Submission(exercise=exercise)
        response_dict       = _post_async_submission(request, exercise, submission, students)
    
    json_response       = simplejson.dumps(response_dict, indent=4)
    return HttpResponse(json_response, content_type="application/json")


def _get_async_submission_info(exercise, students):
    """ 
    This function is used for building a response to a GET request to a 
    asynchronous submission URL. It returns a dictionary containing details
    about the exercise and about the previous submissions for the given 
    user and exercise.
    
    @param exercise: An exercise model that inherits BaseExercise
    @param students: the students submitting the exercise
    @return: a dictionary containing points and submissions 
    """
    
    submissions         = Submission.objects.distinct().filter(exercise=exercise,
                                                               submitters__in=students)
    
    submission_count    = submissions.count()
    
    if submission_count > 0:
        current_points  = submissions.aggregate(Max('grade'))["grade__max"]
    else:
        current_points  = 0
    
    return {"max_points"            : exercise.max_points,
            "max_submissions"       : exercise.max_submissions,
            "current_submissions"   : submission_count,
            "current_points"        : current_points,
            "is_open"               : exercise.is_open(),
           }

def _post_async_submission(request, exercise, submission, students):
    """ 
    This function takes parameters from a POST request and uses them to create or grade a
    submission.
    
    Required parameters in the request are points, max_points and feedback. If errors occur
    or submissions are no longer accepted, a dictionary with an "errors" list will be returned.
    Otherwise a dictionary with "success" will be returned.
    
    @param request: HttpRequest from Django
    @param exercise: An exercise model that inherits BaseExercise
    @param submission: 
    @param students: the students submitting the exercise
    @return: a dictionary containing either errors as a list of strings or a success value of True
    """
    
    # Check if this is a new submission
    if submission.pk == None:
        # New submissions are accepted only if the students are allowed 
        # to submit to this exercise
        is_valid, errors = exercise.is_submission_allowed( students )
    else:
        is_valid    = True
        errors      = []
    
    # Create submission form model and check if it contains errors
    form            = SubmissionCallbackForm(request.POST)
    
    is_valid        = form.is_valid() and is_valid
    
    # Collect form validation errors in error list
    for field in form.errors:
        for err in form.errors[field]:
            errors.append(field + ": " + err)
            # Contains errors, so submission is not allowed
            is_valid = False

    print errors
    
    # If there are no errors, proceed with creating a new submission:
    if is_valid:
        try:
            # Set the given grade
            submission.set_points(form.cleaned_data["points"], form.cleaned_data["max_points"])

            submission.feedback         = form.cleaned_data["feedback"]
            
            # Save all given POST parameters
            submission.set_grading_data(request.POST)

            if form.cleaned_data["error"]:
                submission.set_error()
            else:
                submission.set_ready()

            submission.save()
            
            submission.add_submitters(students)
            
            # Return a dict after successful save
            return {"success": True,
                    "errors": []}
        except Exception, e:
            return {"success": False, 
                    "errors": [str(e)]}
    
    return {"success": False, 
            "errors": errors}

