import logging
from typing import TYPE_CHECKING

from django.contrib import messages
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from lib.email_messages import email_course_error
from lib.remote_page import RemotePage, RemotePageException
from .exercise_page import ExercisePage


if TYPE_CHECKING:
    from exercise.models import LearningObject


logger = logging.getLogger("aplus.protocol")


def load_exercise_page(request, url, last_modified, exercise):
    """
    Loads the exercise page from the remote URL.

    """
    page = ExercisePage(exercise)
    try:
        parse_page_content(
            page,
            RemotePage(url, instance_id=exercise.course_instance.id, stamp=last_modified),
            exercise
        )
    except RemotePageException:
        messages.error(request,
            _('EXERCISE_SERVICE_ERROR_CONNECTION_FAILED'))
        if exercise.id:
            instance = exercise.course_instance
            msg = "Failed to request {}".format(url)
            if instance.visible_to_students and not instance.is_past():
                logger.exception(msg)
                email_course_error(request, exercise, msg)
            else:
                logger.warning(msg)
    return page


def load_feedback_page(request, url, exercise, submission, no_penalties=False):
    """
    Loads the feedback or accept page from the remote URL.
    """
    page = ExercisePage(exercise)
    try:
        data, files = submission.get_post_parameters(request, url)
        remote_page = RemotePage(url, post=True, data=data, files=files, instance_id=exercise.course_instance.id)
        submission.clean_post_parameters()
        parse_page_content(page, remote_page, exercise)
    except RemotePageException:
        page.errors.append(_('ASSESSMENT_SERVICE_ERROR_CONNECTION_FAILED'))
        if exercise.course_instance.visible_to_students:
            msg = "Failed to request {}".format(url)
            logger.exception(msg)
            email_course_error(request, exercise, msg)

    if page.is_loaded:
        submission.feedback = page.clean_content
        if page.is_accepted:
            submission.set_waiting()
            if page.is_graded:
                if page.is_sane():
                    submission.set_points(
                        page.points, page.max_points, no_penalties)
                    submission.set_ready()
                    # Hide unnecessary system wide messages when grader works as expected.
                    # msg = _("The exercise was submitted and graded "
                    #     "successfully. Points: {points:d}/{max:d}").format(
                    #     points=submission.grade,
                    #     max=exercise.max_points
                    # )
                    # if submission.grade < exercise.max_points:
                    #     messages.info(request, msg)
                    # else:
                    #     messages.success(request, msg)
                else:
                    submission.set_error()
                    page.errors.append(
                        format_lazy(
                            _('ASSESSMENT_SERVICE_ERROR_RESPONDED_INVALID_POINTS -- {points:d}, {max:d}, {exercise_max:d}'), # noqa: E501
                            points=page.points,
                            max=page.max_points,
                            exercise_max=exercise.max_points
                        )
                    )
                    if exercise.course_instance.visible_to_students:
                        msg = "Graded with invalid points {:d}/{:d}"\
                            " (exercise max {:d}): {}".format(
                                page.points, page.max_points,
                                exercise.max_points, exercise.service_url)
                        logger.error(msg, extra={"request": request})
                        email_course_error(request, exercise, msg)
            else:
                pass
                # Hide unnecessary system wide messages when grader works as expected.
                # messages.success(request,
                #     _("The exercise was submitted successfully "
                #       "and is now waiting to be graded.")
                # )
        elif page.is_rejected:
            submission.set_rejected()
        else:
            submission.set_error()
            logger.info("No accept or points received: %s",
                exercise.service_url)
            page.errors.append(_('ASSESSMENT_SERVICE_ERROR_RESPONDED_ERROR'))
        submission.save()

    return page


def parse_page_content(
        page: ExercisePage,
        remote_page: RemotePage,
        exercise: 'LearningObject',
        ) -> None:
    """
    Parses exercise page elements.
    """
    page.is_loaded = True

    max_points = remote_page.meta("max-points")
    if max_points != None: # noqa: E711
        page.max_points = int(max_points)
    max_points = remote_page.meta("max_points")
    if max_points != None: # noqa: E711
        page.max_points = int(max_points)

    s = remote_page.meta("status")
    if s == "accepted":
        page.is_accepted = True
        if remote_page.meta("wait"):
            page.is_wait = True
    elif s == "rejected":
        page.is_rejected = True

    meta_title = remote_page.meta("DC.Title")
    if meta_title:
        page.meta["title"] = meta_title
    else:
        page.meta["title"] = remote_page.title()

    description = remote_page.meta("DC.Description")
    if description:
        page.meta["description"] = description

    points = remote_page.meta("points")
    if points != None: # noqa: E711
        page.points = int(points)
        page.is_graded = True
        page.is_accepted = True
        page.is_wait = False

    remote_page.fix_relative_urls()
    remote_page.find_and_replace('data-aplus-exercise', [{
        'id': ('chapter-exercise-' + str(o.order)),
        'data-aplus-exercise': o.get_absolute_url(),
    } for i,o in enumerate(exercise.children.all())])

    page.head = remote_page.head({'data-aplus':True})
    element_selectors = (
        {'id':'aplus'},
        {'id':'exercise'},
        {'id':'chapter'},
        {'class':'entry-content'},
    )
    id_attrs_to_remove = ('exercise', 'chapter', 'aplus')
    page.content, page.clean_content = remote_page.element_or_body(element_selectors, id_attrs_to_remove)
    page.last_modified = remote_page.last_modified()
    page.expires = remote_page.expires()
