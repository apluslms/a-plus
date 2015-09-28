import logging
import socket
from urllib.parse import urlparse

from django.http import HttpResponseForbidden
from django.http.response import HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from userprofile.models import UserProfile
from lib.email_messages import email_course_error
from lib.helpers import extract_form_errors
from .forms import SubmissionCallbackForm
from .models import BaseExercise
from .submission_models import Submission


logger = logging.getLogger('aplus.exercise')


@csrf_exempt
def new_async_submission(request, student_ids, exercise_id, hash_key):
    """
    Creates a new submission for student(s). The view has a student and
    exercise specific URL, which can be authenticated by verifying the hash
    included in the URL.

    When the view is requested with a GET request, a JSON response with
    information about the exercise and previous submissions for the students is
    included. When a POST request is made, the view tries to create a new
    submission for the given students.
    """
    exercise = get_object_or_404(BaseExercise, id=exercise_id)
    user_ids = student_ids.split("-")
    students = UserProfile.objects.filter(id__in=user_ids)
    _, valid_hash = exercise.get_async_hash(students)

    if hash_key != valid_hash:
        return HttpResponseNotFound(_("Invalid hash key in URL."))
    if len(students) != len(user_ids):
        return HttpResponseNotFound(_("Invalid users in URL."))

    return _async_submission_handler(request, exercise, students)


@csrf_exempt
def grade_async_submission(request, submission_id, hash_key):
    """
    Grades a submission asynchronously. The view has a submission specific URL,
    which can be authenticated by verifying the hash included in the URL.

    When the view is requested with a GET request, a JSON response with
    information about the exercise and previous submissions for the students is
    included. When a POST request is made, the view tries to add grading for
    the submission.
    """
    submission = get_object_or_404(Submission, id=submission_id, hash=hash_key)
    exercise = submission.exercise
    students = submission.submitters.all()

    return _async_submission_handler(request, exercise, students, submission)


def _get_service_ip(exercise_url):
    """
    This function takes a full URL as a parameter and returns the IP address
    of the host as a string.
    """
    parse_result = urlparse(exercise_url)
    host = parse_result.netloc.split(":")[0]
    return socket.gethostbyname(host)


def _async_submission_handler(request, exercise, students, submission=None):
    """
    Responses GET with submissions information and grades a submission on POST.

    """
    # Check the IP address matches the host name.
    if request.META["REMOTE_ADDR"] != _get_service_ip(exercise.service_url):
        logger.error('Request IP does not match exercise service URL: %s != %s',
            request.META["REMOTE_ADDR"], exercise.service_url)
        return HttpResponseForbidden(
            _("Only the exercise service is allowed to access this URL."))

    if request.method == "GET":
        return JsonResponse(_get_async_submission_info(exercise, students))

    # Create a new submission if one is not provided
    errors = []
    if submission == None:
        is_valid, errors = exercise.is_submission_allowed(students)
        if not is_valid:
            return JsonResponse({
                "success": False,
                "errors": errors
            })
        submission = Submission.objects.create(exercise=exercise)
        submission.submitters = students

    return JsonResponse(_post_async_submission(
        request, exercise, submission, students, errors))


def _get_async_submission_info(exercise, students):
    """
    Collects details about the exercise and the previous submissions for the
    given students.
    """
    submissions = Submission.objects.filter(
            exercise=exercise,
            submitters__in=students) \
        .order_by('-grade')

    submission_count = submissions.count()
    if submission_count > 0:
        current_points = submissions.first().grade
    else:
        current_points = 0

    return {
        "max_points"            : exercise.max_points,
        "max_submissions"       : exercise.max_submissions,
        "current_submissions"   : submission_count,
        "current_points"        : current_points,
        "is_open"               : exercise.is_open(),
    }


def _post_async_submission(request, exercise, submission, students, errors):
    """
    Creates or grades a submission.

    Required parameters in the request are points, max_points and feedback. If
    errors occur or submissions are no longer accepted, a dictionary with
    "success" is False and "errors" list will be returned.
    """

    # Use form to parse and validate the request.
    form = SubmissionCallbackForm(request.POST)
    errors.extend(extract_form_errors(form))
    if not form.is_valid():
        submission.feedback = _(
            "<div class=\"alert alert-error\">\n"
            "<p>The exercise assessment service is malfunctioning. "
            "Staff has been notified.</p>\n"
            "<p>This submission is now marked as erroneous.</p>\n"
            "</div>")
        submission.set_error()
        submission.save()
        if exercise.course_instance.visible_to_students:
            msg = "Exercise service returned with invalid grade request: {}"\
                .format("\n".join(errors))
            logger.error(msg)
            email_course_error(request, exercise, msg, False)
        return {
            "success": False,
            "errors": errors
        }

    # Grade the submission.
    try:
        submission.set_points(form.cleaned_data["points"],
                              form.cleaned_data["max_points"])
        submission.feedback = form.cleaned_data["feedback"]
        submission.grading_data = request.POST

        if form.cleaned_data["error"]:
            submission.set_error()
        else:
            submission.set_ready()
        submission.save()
        return {
            "success": True,
            "errors": []
        }

    # Produce error if something goes wrong during saving the points.
    except Exception as e:
        logger.exception("Unexpected error while saving grade");
        return {
            "success": False,
            "errors": [repr(e)]
        }
