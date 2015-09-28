import traceback
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse


def email_course_error(request, exercise, message):
    """
    Sends error message to course teachers or technical support emails if set.
    """
    instance = exercise.course_instance
    if instance.technical_error_emails:
        recipients = instance.technical_error_emails.split(",")
    else:
        recipients = (p.user.email for p in instance.course.teachers.all())

    subject = settings.EXERCISE_ERROR_SUBJECT.format(
        course=instance.course.code,
        exercise=str(exercise.name))
    body = settings.EXERCISE_ERROR_DESCRIPTION.format(
        message=message,
        exercise_edit_url=request.build_absolute_uri(
            reverse('model-edit', kwargs={
                "course": instance.course.url,
                "instance": instance.url,
                "model": 'exercise',
                "id": exercise.id})),
        course_edit_url=request.build_absolute_uri(
            instance.get_url('course-details')),
        error_trace=traceback.format_exc(),
        request_fields=repr(request))
    send_mail(subject, body, settings.SERVER_EMAIL, recipients, True)
