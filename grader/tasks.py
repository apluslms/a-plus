'''
An asychronous grading task that is queued and later run by queue workers.
Requires running Celery which requires running broker e.g. RabbitMQ.
'''
import logging
import os

# Set Django configuration path for celeryd.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grader.settings')


from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import translation
from pyrabbit.api import Client
from access.config import ConfigParser, ConfigError
from grader.runactions import runactions
from util.http import post_system_error, post_result
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

# Check settings object and validate base dir.
if len(settings.BASE_DIR) < 2:
    raise ConfigError("Configuration problem, BASE_DIR: %s", settings.BASE_DIR)

# Create and configure Celery instance.
app = Celery("tasks", broker=settings.CELERY_BROKER)
app.conf.update(
    CELERYD_TASK_TIME_LIMIT=settings.CELERY_TASK_KILL_SEC,
    CELERYD_TASK_SOFT_TIME_LIMIT=settings.CELERY_TASK_LIMIT_SEC,
    CELERYD_CONCURRENCY=1,
    CELERYD_PREFETCH_MULTIPLIER=1,
    CELERYD_HIJACK_ROOT_LOGGER=True,
)

# Create rabbitmq management client.
client = None
path = None
if settings.CELERY_BROKER:
    uri = urlparse(settings.CELERY_BROKER)
    client = Client(
        "{}:{:d}".format(uri.hostname, settings.RABBITMQ_MANAGEMENT["port"]),
        uri.username, settings.RABBITMQ_MANAGEMENT["password"])
    path = uri.path

# Hold on to the latest exercise configuration.
config = ConfigParser()

LOGGER = logging.getLogger('main')


@app.task(ignore_result=True)
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


def queue_length():
    '''
    Gets the length of the queue.

    @rtype: C{int}
    @return: a number of queued tasks
    '''
    try:
        if client:
            return client.get_queue_depth(path, "celery")
    except Exception:
        LOGGER.exception("Queue length is unknown.")
    return 0
