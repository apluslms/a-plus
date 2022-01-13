import logging
import traceback
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .helpers import build_aplus_url


logger = logging.getLogger('aplus.lib.email_messages')


def email_course_instance(instance, subject, message, everyone=False) -> bool:
    """
    Sends an email to a course instance's technical support emails or teachers if technical support not set.
    If everyone == True, sends emails to teachers anyway.
    """
    recipients = []
    if instance.technical_error_emails:
        recipients = instance.technical_error_emails.split(",")
    if everyone or not recipients:
        recipients = instance.teachers.exclude(user__email='').values_list("user__email", flat=True)

    if not recipients:
        raise ValueError("No recipients")

    try:
        return send_mail(subject, message, settings.SERVER_EMAIL, recipients, True) == 1
    except:
        logger.exception('Failed to send course instance emails.')
        raise


def email_course_error(request, exercise, message, exception=True):
    """
    Sends error message to course instance's teachers or technical support emails if set.
    """
    instance = exercise.course_instance

    error_trace = "-"
    if exception:
        error_trace = traceback.format_exc()

    if request:
        request_fields = repr(request)
    else:
        request_fields = "No request available"

    subject = settings.EXERCISE_ERROR_SUBJECT.format(
        course=instance.course.code,
        exercise=str(exercise))
    body = settings.EXERCISE_ERROR_DESCRIPTION.format(
        message=message,
        exercise_url=build_aplus_url(
            exercise.get_absolute_url(), user_url=True),
        course_edit_url=build_aplus_url(
            instance.get_url('course-details'), user_url=True),
        error_trace=error_trace,
        request_fields=request_fields)

    try:
        email_course_instance(instance, subject, body)
    except:
        pass
