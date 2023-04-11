import os
import celery
import datetime
from datetime import timedelta
import logging
from dateutil.relativedelta import relativedelta
from time import sleep

from django.conf import settings


logger = logging.getLogger('aplus.celery')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aplus.settings')

app = celery.Celery('aplus')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if hasattr(settings, 'SIS_ENROLL_SCHEDULE'):
        sender.add_periodic_task(settings.SIS_ENROLL_SCHEDULE, enroll.s(), name='enroll')

    if settings.SUBMISSION_EXPIRY_TIMEOUT:
        # Run timed check twice in timeout period, for more timely retries
        sender.add_periodic_task(settings.SUBMISSION_EXPIRY_TIMEOUT/2, retry_submissions.s(), name='retry_submissions')

@app.task
def enroll():
    """
    Traverse the currently open courses that are linked to SIS and update enrollments.
    """
    from course.models import CourseInstance # pylint: disable=import-outside-toplevel
    now = datetime.datetime.now(datetime.timezone.utc)
    # Enroll students for active courses, or those that will start in 14 days
    courses = CourseInstance.objects.filter(
        ending_time__gt=now,
        starting_time__lt=now + timedelta(days=14),
        sis_enroll=True,
    )
    for i in courses:
        i.enroll_from_sis()
        if settings.SIS_ENROLL_DELAY:
            sleep(settings.SIS_ENROLL_DELAY)

@app.task
def retry_submissions():
    # pylint: disable-next=import-outside-toplevel
    from exercise.submission_models import PendingSubmission

    # Recovery state: only send one grading request to probe the state of grader
    # We pick the one with most attempts, so that total_retries comes down more quickly
    # when things are back to normal, and we can return to normal state
    if not PendingSubmission.objects.is_grader_stable():
        pending = PendingSubmission.objects.order_by('-num_retries').first()
        # pylint: disable-next=logging-fstring-interpolation
        logging.info(f"Recovery state: retrying expired submission {pending.submission}")
        pending.submission.exercise.grade(pending.submission)
        return

    # Stable state: retry all expired submissions
    expiry_time = datetime.datetime.now(datetime.timezone.utc) - relativedelta(
        seconds=settings.SUBMISSION_EXPIRY_TIMEOUT
    )
    expired = PendingSubmission.objects.filter(submission_time__lt=expiry_time)

    for pending in expired:
        if pending.submission.exercise.can_regrade:
            # pylint: disable-next=logging-fstring-interpolation
            logger.info(f"Retrying expired submission {pending.submission}")
            pending.submission.exercise.grade(pending.submission)
            sleep(0.5)  # Delay 500 ms to avoid choking grader
