import traceback
from django.conf import settings
from django.core.mail import send_mail


def email_course_error(course_instance, message):
    """
    Sends error message to course teachers or technical support emails if set.
    """
    if course_instance.technical_error_emails:
        recipients = course_instance.technical_error_emails.split(",")
    else:
        recipients = (p.user.email for p in course_instance.course.teachers)

    course = course_instance.course
    header = "A+ exercise error occured in {} {}".format(
        course.code, course.name)
    body = "{}\n\n{}\n\n{}".format(
        settings.EXERCISE_ERROR_DESCRIPTION, message, traceback.format_exc())
    send_mail(header, body, settings.SERVER_EMAIL, recipients, True)
