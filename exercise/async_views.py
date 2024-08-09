import logging
from django.utils.translation import gettext_lazy as _

from lib.email_messages import email_course_error
from lib.helpers import extract_form_errors
from notification.models import Notification
from .forms import SubmissionCallbackForm
from lti_tool.utils import send_lti_points

logger = logging.getLogger('aplus.exercise')


def _post_async_submission(request, exercise, submission, errors=None):
    """
    Creates or grades a submission.

    Required parameters in the request are points, max_points and feedback. If
    errors occur or submissions are no longer accepted, a dictionary with
    "success" is False and "errors" list will be returned.
    """
    if not errors:
        errors = []

    # The feedback field may contain null characters, which would invalidate
    # the form before its clean method is executed. So replace them beforehand.
    post_data = request.POST.copy()
    feedback = post_data.get('feedback')
    if feedback:
        post_data['feedback'] = feedback.replace('\x00', '\\x00')

    # Use form to parse and validate the request.
    form = SubmissionCallbackForm(post_data)
    errors.extend(extract_form_errors(form))
    if not form.is_valid():
        submission.feedback = _("ERROR_ALERT_EXERCISE_ASSESSMENT_SERVICE_MALFUNCTIONING")
        submission.set_error()
        submission.save()
        if exercise.course_instance.visible_to_students:
            msg = "Exercise service returned with invalid grade request: {}"\
                .format("\n".join(errors))
            logger.error(msg, extra={"request": request})
            email_course_error(request, exercise, msg, False)
        return {
            "success": False,
            "errors": errors
        }

    # Grade the submission.
    try:
        submission.set_points(form.cleaned_data["points"],
                              form.cleaned_data["max_points"])
        submission.feedback = form.cleaned_data["feedback"]
        submission.grading_data = post_data

        # If A+ is used as LTI Tool and the assignment uses the Acos-server,
        # the submission has not been able to save the LTI launch id before
        # this phase. The launch id is needed for sending the grade to
        # the LTI Platform.
        if submission.meta_data == "":
            submission.meta_data = {}
        if (form.cleaned_data["lti_launch_id"]
                and submission.meta_data.get("lti-launch-id") is None):
            submission.meta_data["lti-launch-id"] = form.cleaned_data["lti_launch_id"]
        if (form.cleaned_data["lti_session_id"]
                and submission.meta_data.get("lti-session-id") is None):
            submission.meta_data["lti-session-id"] = form.cleaned_data["lti_session_id"]

        if form.cleaned_data["error"]:
            submission.set_error()
        else:
            submission.set_ready()
        submission.save()

        if form.cleaned_data["notify"]:
            regrade_when_notification_seen = form.cleaned_data["regrade_when_notification_seen"]
            Notification.send(None, submission, regrade_when_seen=regrade_when_notification_seen)
        else:
            Notification.remove(submission)

        # If the submission was made through LTI, send results back to the platform.
        if submission.lti_launch_id:
            send_lti_points(request, submission)

        return {
            "success": True,
            "errors": []
        }

    # Produce error if something goes wrong during saving the points.
    except Exception as e:
        logger.exception("Unexpected error while saving grade"
            " for {} and submission id {:d}".format(str(exercise), submission.id));
        return {
            "success": False,
            "errors": [repr(e)]
        }
