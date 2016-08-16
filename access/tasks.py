from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import translation
import logging

from access.config import config
from grader.runactions import runactions
from util.affinity import set_affinity
from util.http import post_system_error, post_result


LOGGER = logging.getLogger('main')


@shared_task
def grade(course_key, exercise_key, lang, submission_url, submission_dir, user_ids='', submission_number=1):
    '''
    Grades the submission using configured grading actions.

    @type course_key: C{str}
    @param course: a course key
    @type exercise: C{str}
    @param exercise: an exercise key
    @type lang: C{str}
    @param lang: a language code
    @type submission_url: C{str}
    @param submission_url: a submission URL where grader should POST result
    @type submission_dir: C{str}
    @param submission_dir: a submission directory where submitted files are stored
    @type user_ids: C{str}
    @param user_ids: user id(s) of the submitter(s) for personalized exercises
    @type submission_number: C{int}
    @param submission_number: ordinal number of the submission (parameter in the grader protocol)
    '''
    set_affinity(settings.CELERY_AFFINITIES)
    translation.activate(lang)
    (course, exercise) = config.exercise_entry(course_key, exercise_key, lang=lang)
    if course is None or exercise is None:
        LOGGER.error("Unknown exercise \"%s/%s\" for \"%s\"", course_key, exercise_key, submission_url)
        post_system_error(submission_url, course)

    try:
        LOGGER.debug("Grading \"%s/%s\" for \"%s\"", course_key, exercise_key, submission_url)
        r = runactions(course, exercise, submission_dir, user_ids, submission_number)
        if r["result"]["error"]:
            level = 40 if r["result"]["error"] == "error" else 30
            LOGGER.log(level, "Grading \"%s/%s\" for \"%s\" failed. "
                "Expected success for the last action:\n\n%s\n\n%s",
                course_key, exercise_key, submission_url,
                r["result"]["tests"][-1]["out"],
                r["result"]["tests"][-1]["err"])
        else:
            LOGGER.debug("Finished grading with points: %d/%d",
                r["result"]["points"], r["result"]["max_points"])
        post_result(submission_url, course, exercise, r["template"], r["result"])

    except SoftTimeLimitExceeded:
        LOGGER.error("Grading timeout \"%s/%s\" for \"%s\"", course_key, exercise_key, submission_url)
        post_result(submission_url, course, exercise, "access/task_timeout.html", { "error": True })

    except Exception:
        LOGGER.exception("Grading error \"%s/%s\" for \"%s\"", course_key, exercise_key, submission_url)
        post_system_error(submission_url, course, exercise)
