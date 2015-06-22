import hashlib
import hmac
import logging
import urllib

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from exercise.remote.exercise_page import ExercisePage
from lib.MultipartPostHandler import MultipartPostHandler


logger = logging.getLogger("aplus.exercise.remote")


def load_exercise_page(request, exercise, students):
    """
    Loads the exercise page from the remote URL.
    
    """
    try:
        opener = urllib.request.build_opener()
        response_body = opener.open(
            get_load_exercise_url(request, exercise, students),
            timeout=20
        ).read()
        return ExercisePage(exercise, response_body)
    except Exception:
        logger.exception("Failed to load exercise: %s", exercise.service_url)
        messages.error(request, _("Connecting to the exercise service failed!"))
    return ExercisePage(exercise)


def load_feedback_page(request, exercise, submission, no_penalties=False):
    """
    Loads the feedback or accept page from the remote URL.
    
    """
    page = None
    try:
        opener = urllib.request.build_opener(MultipartPostHandler)
        params = submission.get_post_parameters()
        response_body = opener.open(
            get_grade_exercise_url(request, exercise, submission),
            params,
            timeout=50
        ).read()
        submission.clean_post_parameters(params)
        page = ExercisePage(exercise, response_body)
    except Exception:
        logger.exception("Failed to submit exercise: %s", exercise.service_url)
        messages.error(request, _("Connecting to the assessment service failed!"))

    if page:
        submission.feedback = page.content
        if page.is_accepted:
            submission.set_waiting()
        else:
            submission.set_error()
            logger.error("No accept or points received: %s", exercise.service_url)
            messages.error(request,
                _("Assessment service gave erroneous response. "
                  "<small>(No accept or points received)</small>"))
        
        if page.is_graded:
            if page.is_sane():
                submission.set_points(
                    page.points, page.max_points, no_penalties)
                submission.set_ready()
                messages.success(request,
                    _("The exercise was submitted and graded successfully. "
                      "Points: {points:d}/{max:d}").format(
                        points=submission.grade,
                        max=exercise.max_points
                    ))
            else:
                submission.set_error()
                logger.error("Insane grading %d/%d: %s",
                    page.points, page.max_points, exercise.service_url)
                messages.error(request,
                    _("Assessment service gave erroneous response. "
                      "<small>(Points: {points:d}/{max:d}, "
                      "exercise max {exercise_max:d})</small>").format(
                        points=page.points,
                        max=page.max_points,
                        exercise_max=exercise.max_points
                    ))
        else:
            messages.success(request,
                _("The exercise was submitted successfully "
                  "and is now waiting to be graded."))
        submission.save()

    return page
 

def get_new_async_hash(exercise, students):
    student_str = "-".join(
        sorted(str(userprofile.id) for userprofile in students)
    )
    identifier = "{}.{:d}".format(student_str, exercise.id)
    hash_key = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        msg=identifier.encode('utf-8'),
        digestmod=hashlib.sha256
    )
    return student_str, hash_key.hexdigest()


def get_load_exercise_url(request, exercise, students):
    student_str, hash_key = get_new_async_hash(exercise, students)
    return _build_service_url(request, exercise, reverse(
        "exercise.async_views.new_async_submission", kwargs={
            "exercise_id": exercise.id,
            "student_ids": student_str,
            "hash_key": hash_key
        }))


def get_grade_exercise_url(request, exercise, submission):
    return _build_service_url(request, exercise, reverse(
        "exercise.async_views.grade_async_submission", kwargs={
            "submission_id": submission.id,
            "hash_key": submission.hash
        }))


def _build_service_url(request, exercise, submission_url):
    """
    Generates complete URL with added parameters to the exercise service.
    """
    params = {
        "max_points": exercise.max_points,
        "submission_url": request.build_absolute_uri(submission_url),
    }
    delimiter = "&" if "?" in exercise.service_url else "?"
    return exercise.service_url + delimiter \
        + urllib.parse.urlencode(params)
