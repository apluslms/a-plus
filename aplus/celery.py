import os
import celery
import datetime
from datetime import timedelta
from time import sleep

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aplus.settings')

app = celery.Celery('aplus')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if hasattr(settings, 'SIS_ENROLL_SCHEDULE'):
        sender.add_periodic_task(settings.SIS_ENROLL_SCHEDULE, enroll.s(), name='enroll')

@app.task
def enroll():
    """
    Traverse the currently open courses that are linked to SIS and update enrollments.
    """
    from course.models import CourseInstance
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
