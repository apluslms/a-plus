import logging
import traceback
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

logger = logging.getLogger('lib.email_messages')


def email_course_error(request, exercise, message, exception=True):
    """
    Sends error message to course teachers or technical support emails if set.
    """
    instance = exercise.course_instance
    if instance.technical_error_emails:
        recipients = instance.technical_error_emails.split(",")
    else:
        recipients = (p.user.email for p in instance.course.teachers.all() if p.user.email)

    error_trace = "-"
    if exception:
        error_trace = traceback.format_exc()

    subject = settings.EXERCISE_ERROR_SUBJECT.format(
        course=instance.course.code,
        exercise=str(exercise))
    body = settings.EXERCISE_ERROR_DESCRIPTION.format(
        message=message,
        exercise_url=request.build_absolute_uri(
            exercise.get_absolute_url()),
        course_edit_url=request.build_absolute_uri(
            instance.get_url('course-details')),
        error_trace=error_trace,
        request_fields=repr(request))
    if recipients:
        try:
            send_mail(subject, body, settings.SERVER_EMAIL, recipients, True)
        except Exception as e:
            logger.exception('Failed to send error emails.')
