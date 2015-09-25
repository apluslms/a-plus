import logging

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from lib.email_messages import email_course_error
from lib.remote_page import RemotePage, RemotePageException
from .exercise_page import ExercisePage


logger = logging.getLogger("aplus.protocol")


def load_exercise_page(request, url, exercise):
    """
    Loads the exercise page from the remote URL.

    """
    page = ExercisePage(exercise)
    try:
        parse_page_content(page, RemotePage(url))
    except RemotePageException:
        messages.error(request,
            _("Connecting to the exercise service failed!"))
        if exercise.id and exercise.course_instance.visible_to_students:
            msg = "Failed to request {}".format(url)
            logger.exception(msg)
            email_course_error(exercise.instance, msg)
    return page


def load_feedback_page(request, url, exercise, submission, no_penalties=False):
    """
    Loads the feedback or accept page from the remote URL.

    """
    page = ExercisePage(exercise)
    try:
        data, files = submission.get_post_parameters()
        remote_page = RemotePage(url, post=True, data=data, files=files)
        submission.clean_post_parameters()
        parse_page_content(page, remote_page)
    except RemotePageException:
        messages.error(request,
            _("Connecting to the assessment service failed!"))
        if exercise.id and exercise.course_instance.visible_to_students:
            msg = "Failed to request {}".format(url)
            logger.exception(msg)
            email_course_error(exercise.instance, msg)

    if page.is_loaded:
        submission.feedback = page.content
        if page.is_accepted:
            submission.set_waiting()
            if page.is_graded:
                if page.is_sane():
                    submission.set_points(
                        page.points, page.max_points, no_penalties)
                    submission.set_ready()
                    messages.success(request,
                        _("The exercise was submitted and graded "
                          "successfully. Points: {points:d}/{max:d}").format(
                            points=submission.grade,
                            max=exercise.max_points
                        ))
                else:
                    submission.set_error()
                    messages.error(request,
                        _("Assessment service responded with invalid score. "
                          "Points: {points:d}/{max:d} "
                          "(exercise max {exercise_max:d})").format(
                            points=page.points,
                            max=page.max_points,
                            exercise_max=exercise.max_points
                        )
                    )
                    msg = "Insane grading {:d}/{:d} (exercise max {:d}): {}"\
                        .format(page.points, page.max_points,
                            exercise.max_points, exercise.service_url)
                    logger.error(msg)
                    email_course_error(exercise.instance, msg)
            else:
                messages.success(request,
                    _("The exercise was submitted successfully "
                      "and is now waiting to be graded.")
                )
        else:
            submission.set_error()
            logger.info("No accept or points received: %s",
                exercise.service_url)
            messages.error(request,
                _("Assessment service responded with error."))
        submission.save()

    return page


def parse_page_content(page, remote_page):
    """
    Parses exercise page elements.
    """
    page.is_loaded = True

    max_points = remote_page.meta("max-points")
    if max_points != None:
        page.max_points = int(max_points)
    max_points = remote_page.meta("max_points")
    if max_points != None:
        page.max_points = int(max_points)

    if remote_page.meta("status") == "accepted":
        page.is_accepted = True
        if remote_page.meta("wait"):
            page.is_wait = True

    meta_title = remote_page.meta("DC.Title")
    if meta_title:
        page.meta["title"] = meta_title
    else:
        page.meta["title"] = remote_page.title()

    description = remote_page.meta("DC.Description")
    if description:
        page.meta["description"] = description

    points = remote_page.meta("points")
    if points != None:
        page.points = int(points)
        page.is_graded = True
        page.is_accepted = True
        page.is_wait = False

    page.content = remote_page.element_or_body("exercise")
