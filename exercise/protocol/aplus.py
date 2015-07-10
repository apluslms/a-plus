import logging

from bs4 import BeautifulSoup
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
import requests

from .exercise_page import ExercisePage


logger = logging.getLogger("aplus.protocol")


def load_exercise_page(request, url, exercise):
    """
    Loads the exercise page from the remote URL.

    """
    page = ExercisePage(exercise)
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            response.raise_for_status()
        parse_page_content(page, response.text)
    except requests.exceptions.RequestException:
        logger.exception("Failed to load exercise: %s", exercise.service_url)
        messages.error(request, _("Connecting to the exercise service failed!"))
    return page


def load_feedback_page(request, url, exercise, submission, no_penalties=False):
    """
    Loads the feedback or accept page from the remote URL.

    """
    page = ExercisePage(exercise)
    try:
        data, files = submission.get_post_parameters()
        response = requests.post(url, data=data, files=files, timeout=50)
        submission.clean_post_parameters()
        if response.status_code != 200:
            response.raise_for_status()
        parse_page_content(page, response.text)
    except requests.exceptions.RequestException:
        logger.exception("Failed to submit exercise: %s", exercise.service_url)
        messages.error(request, _("Connecting to the assessment service failed!"))

    if page.is_loaded:
        submission.feedback = page.content
        if page.is_accepted:
            submission.set_waiting()
        else:
            submission.set_error()
            logger.error("No accept or points received: %s", exercise.service_url)
            messages.error(request, _("Assessment service responded with error."))
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
                logger.error("Insane grading %d/%d (exercise max %d): %s",
                    page.points,
                    page.max_points,
                    exercise.max_points,
                    exercise.service_url
                )
                messages.error(request,
                    _("Assessment service responded with invalid score. "
                      "Points: {points:d}/{max:d} "
                      "(exercise max {exercise_max:d})").format(
                        points=page.points,
                        max=page.max_points,
                        exercise_max=exercise.max_points
                    )
                )
        else:
            messages.success(request,
                _("The exercise was submitted successfully "
                  "and is now waiting to be graded.")
            )
        submission.save()

    return page


def parse_page_content(page, html):
    """
    Parses page from HTML.

    """
    page.is_loaded = True
    soup = BeautifulSoup(html)

    head = soup.find("head")
    if head:
        max_points = _get_value_from_soup(head, "meta", "value", {"name": "max-points"})
        if max_points != None:
            page.max_points = int(max_points)
        max_points = _get_value_from_soup(head, "meta", "value", {"name": "max_points"})
        if max_points != None:
            page.max_points = int(max_points)

        if _get_value_from_soup(head, "meta", "value", {"name": "status"}) == "accepted":
            page.is_accepted = True
            if _get_value_from_soup(head, "meta", "value", {"name": "wait"}):
                page.is_wait = True

        meta_title = _get_value_from_soup(head, "meta", "content", {"name": "DC.Title"})
        if meta_title:
            page.meta["title"] = meta_title
        else:
            title = soup.find("title")
            if title:
                page.meta["title"] = title.contents

        description = _get_value_from_soup(head, "meta", "content", {"name": "DC.Description"})
        if description:
            page.meta["description"] = description

        points = _get_value_from_soup(head, "meta", "value", {"name": "points"})
        if points != None:
            page.points = int(points)
            page.is_graded = True
            page.is_accepted = True
            page.is_wait = False

    exercise_div = soup.body.find("div", {"id": "exercise"})
    if exercise_div != None:
        page.content = exercise_div.renderContents()
    else:
        page.content = soup.body.renderContents()


def _get_value_from_soup(soup, tag_name, attribute, parameters={}, default=None):
    """
    This is a helper function for finding a specific attribute of an element from
    a HTML soup. The element may be searched with a tag name and parameters. If the
    element or attribute is not found, the 'default' or None value will be returned.

    @param soup: a BeautifulSoup object
    @param tag_name: the name of an HTML tag as a string, for example "div"
    @param attribute: the attribute to read from the tag
    @param parameters: an optional dictionary of keys and values which the element must match
    @param default: a value, which will be returned if no matching element or attribute is found

    @return: the value of the requested attribute from the HTML element. If matching
        value is not found the given default or None is returned
    """
    element = soup.find(tag_name, parameters)
    if element != None:
        return element.get(attribute, default)
    return default
