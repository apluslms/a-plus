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
from access.config import ConfigParser, ConfigError
from grader.runactions import runactions
from util.http import post_system_error, post_result


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

# Hold on to the latest exercise configuration.
config = ConfigParser()

LOGGER = logging.getLogger('main')


@app.task(ignore_result=True)
def grade(course_key, exercise_key, lang, submission_url, submission_dir):
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
    '''
    translation.activate(lang)
    (course, exercise) = config.exercise_entry(course_key, exercise_key, lang=lang)
    if course is None or exercise is None:
        LOGGER.error("Unknown exercise \"%s/%s\" for \"%s\"", course_key, exercise_key, submission_url)
        post_system_error(submission_url, course)

    try:
        LOGGER.debug("Grading \"%s/%s\" for \"%s\"", course_key, exercise_key, submission_url)
        r = runactions(course, exercise, submission_dir)
        if r["result"]["error"]:
            LOGGER.error("Grading \"%s/%s\" for \"%s\" failed. "
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
    if settings.CELERY_BROKER:
        try:
            from librabbitmq import Connection
            host = settings.CELERY_BROKER.split("//")[1].split("@")[1]
            connection = Connection(host=host, userid="guest", password="guest", virtual_host="/")
            channel = connection.channel()
            name, jobs, consumers = channel.queue_declare(queue="celery", passive=True)
            channel.close()
            connection.close()
            return jobs
        except ImportError:
            LOGGER.exception("Failed to import librabbitmq module. Queue length is unknown.")
    return 0
