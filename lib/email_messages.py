import logging
import traceback
from django.conf import settings
from django.core.mail import send_mail, send_mass_mail

from .helpers import Enum, build_aplus_url
from course.models import CourseInstance
from userprofile.models import UserProfile


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
    except: # pylint: disable=bare-except
        pass


def email_course_students_and_staff(
        instance: CourseInstance,
        subject: str,
        message: str,
        student_audience: Enum = CourseInstance.ENROLLMENT_AUDIENCE.ALL_USERS,
        include_staff: bool = False,
        ) -> int:
    """
    Sends an email to students and staff of the course. Audience parameter controls whether the mail goes
    to all, just internal, or just external students.
    Returns number of emails sent, or -1 in case of error.
    """
    student_querys = {
        CourseInstance.ENROLLMENT_AUDIENCE.ALL_USERS: instance.students,
        CourseInstance.ENROLLMENT_AUDIENCE.INTERNAL_USERS:
            instance.students.filter(organization=settings.LOCAL_ORGANIZATION),
        CourseInstance.ENROLLMENT_AUDIENCE.EXTERNAL_USERS:
            instance.students.exclude(organization=settings.LOCAL_ORGANIZATION),
    }
    recipients = (
        student_querys
        .get(student_audience, UserProfile.objects.none())
        .exclude(user__email='')
        .values_list("user__email", flat=True)
    )
    if include_staff:
        recipients = recipients.union(
            instance.course_staff
            .exclude(user__email='')
            .values_list("user__email", flat=True)
        )

    emails = tuple(map(lambda x: (subject, message, settings.SERVER_EMAIL, [x]), recipients))

    try:
        return send_mass_mail(emails)
    except: # pylint: disable=bare-except
        logger.exception('Failed to send course instance emails.')
        return -1
