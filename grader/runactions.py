from django.core.exceptions import ImproperlyConfigured
import logging

from access.config import ConfigError
from util.files import clean_submission_dir
from util.importer import import_named
from util.http import get_json
from util.personalized import regenerate_user_exercise
import requests

LOGGER = logging.getLogger('main')


def runactions(course, exercise, submission_dir, user_ids="", submission_url=""):
    '''
    Runs configured grading actions for an exercise submission.

    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type submission_dir: C{str}
    @param submission_dir: a submission directory where submitted files are stored
    @type user_ids: C{str}
    @param user_ids: user id(s) of the submitter(s) for personalized exercises
    @type submission_url: C{str}
    @param submission_url: submission_url parameter in the grader protocol
    @rtype: C{dict}
    @return: template = template name, result = points, max_points, tests
    '''
    total_points = 0
    max_points = 0
    total_result = []
    error = False
    has_appendixes = False

    # Try to run the grading actions.
    try:
        for action in exercise["actions"]:
            exgrader = None
            try:
                exgrader = import_named(course, action["type"])
            except ImproperlyConfigured as e:
                raise ConfigError("Invalid action \"type\" in exercise configuration.", e)

            # Run the exercise grader action
            LOGGER.debug("Running action \"%s\"", action["type"])
            if action["type"] == "grader.actions.prepare" or \
                    action["type"] == "grader.actions.store_user_files":
                r = exgrader(course, exercise, action, submission_dir, user_ids)
            else:
                r = exgrader(course, exercise, action, submission_dir)
            has_appendixes = has_appendixes or \
                ("appendix" in r and r["appendix"])

            # Configured template values.
            if "title" in action:
                r["title"] = action["title"]
            if "html" in action and action["html"]:
                r["html"] = True

            # Override with configured points.
            if "points" in action:
                r["max_points"] = action["points"]
                if r["stop"]:
                    r["points"] = 0
                else:
                    r["points"] = action["points"]
            elif "max_points" in action:
                r["max_points"] = action["max_points"]
                if r["points"] > action["max_points"]:
                    r["points"] = action["max_points"]

            # Sum total numbers.
            total_result.append(r)
            total_points += r["points"]
            if "max_points" in r:
                max_points += r["max_points"]
            if r["stop"]:
                if "expect_success" in action:
                    error = action["expect_success"]
                if not ("continue_after_error" in action and action["continue_after_error"]):
                    break # skip the subsequent actions

        # Override with configured max points.
        if "max_points" in exercise:
            max_points = exercise["max_points"]

        # Check the points are in range.
        if total_points > max_points:
            total_points = max_points
        elif total_points < 0:
            total_points = 0

        # Determine template.
        template = None
        if "feedback_template" in exercise:
            template = exercise["feedback_template"]
        else:
            template = "access/task_success.html"

        # check if exercise requires regeneration (personalized and regeneration submit limit is set)
        if "personalized" in exercise and exercise["personalized"] and \
                "max_submissions_before_regeneration" in exercise:
            try:
                # GET submission_url to see the submission count of the student
                info_json = get_json(submission_url)
                if info_json["submission_ordinal_number"] % exercise["max_submissions_before_regeneration"] == 0:
                    regenerate_user_exercise(course, exercise, user_ids)
            except (requests.exceptions.HTTPError, requests.exceptions.Timeout, ValueError) as e:
                LOGGER.debug("GET submission_url failed while regenerating user's exercise: %s", str(e))
        
        return {
            "template": template,
            "result": {
                "points": total_points,
                "max_points": max_points,
                "tests": total_result,
                "error": error,
                "has_appendixes": has_appendixes,
            }
        }
        
    finally:
        clean_submission_dir(submission_dir)
