import logging
from typing import Any, Optional, Tuple

from django.conf import settings
from django.contrib.auth.models import User
from django.http.request import HttpRequest
from pylti1p3.grade import Grade
from pylti1p3.contrib.django import DjangoMessageLaunch, DjangoCacheDataStorage, DjangoDbToolConf
from pylti1p3.lineitem import LineItem
from pylti1p3.message_launch import TLaunchData
from pylti1p3.exception import LtiException, LtiServiceException

from course.models import CourseInstance


logger = logging.getLogger('aplus.lti_tool')

def get_launch_url(request):
    target_link_uri = request.POST.get('target_link_uri', request.GET.get('target_link_uri'))
    if not target_link_uri:
        logger.error('Missing "target_link_uri" param')
        raise Exception('Missing "target_link_uri" param') # pylint: disable=broad-exception-raised
    return target_link_uri

def get_tool_conf():
    # Cannot default to DjangoDbToolConf() in settings.py due to models not being initialized yet
    if hasattr(settings, "LTI_TOOL_CONF"):
        return settings.LTI_TOOL_CONF
    return DjangoDbToolConf()

def get_launch_data_storage():
    return DjangoCacheDataStorage()

def parse_lti_session_params(
        request: HttpRequest,
        ) -> Tuple[Optional[DjangoMessageLaunch], Optional[TLaunchData]]:
    launch_id = request.session.get("lti-launch-id", None)
    if not launch_id:
        return None, None
    tool_conf = get_tool_conf()
    message_launch = DjangoMessageLaunch.from_cache(
        launch_id,
        request,
        tool_conf,
        launch_data_storage=get_launch_data_storage(),
    )
    message_launch_data = message_launch.get_launch_data()
    return message_launch, message_launch_data

def has_lti_access_to_course(
        request: HttpRequest,
        view: Optional[Any],
        target_course_instance: CourseInstance,
        ) -> bool:
    lti_scope = getattr(view, 'lti_scope', None)
    if not lti_scope:
        _message_launch, message_launch_data = parse_lti_session_params(request)
        if message_launch_data:
            lti_scope = message_launch_data.get("https://purl.imsglobal.org/spec/lti/claim/custom")
            if not lti_scope:
                return False
        else:
            return False
    return (
        lti_scope.get('course_slug') == target_course_instance.course.url
        and lti_scope.get('instance_slug') == target_course_instance.url
    )

def send_lti_points(request, submission):
    from exercise.exercise_summary import UserExerciseSummary # pylint: disable=import-outside-toplevel
    exercise = submission.exercise
    request.COOKIES['lti1p3-session-id'] = submission.meta_data.get('lti-session-id')
    try:
        launch = DjangoMessageLaunch.from_cache(
            submission.lti_launch_id,
            request,
            get_tool_conf(),
            launch_data_storage=get_launch_data_storage(),
        )
    except LtiException:
        logger.warning(
            "Failed to send LTI points for submission id '%s' "
            "because the LTI launch data was not found. "
            "The LTI launch id saved in the submission may have "
            "expired in the cache.",
            submission.pk,
        )
        return

    try:
        username = launch.get_launch_data()['https://purl.imsglobal.org/spec/lti/claim/ext']['user_username']
    except (KeyError, TypeError):
        username = launch.get_launch_data()['email']

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warning("Tried to send LTI points for a non-existing user '%s'.", username)
        return

    # Moodle does not have gradebook entries for teachers - don't send result if submitter is a teacher
    is_course_teacher = exercise.course_instance.is_teacher(user)
    if not is_course_teacher:
        summary = UserExerciseSummary(exercise, user)
        best_submission = summary.best_submission
        ags = launch.get_ags()
        grade = Grade()
        (grade.set_score_given(best_submission.grade)
            .set_timestamp(best_submission.submission_time.strftime('%Y-%m-%dT%H:%M:%S+0000'))
            .set_score_maximum(exercise.max_points)
            .set_activity_progress('Completed')
            .set_grading_progress('FullyGraded')
            .set_user_id(launch.get_launch_data().get('sub')))
        line_item = LineItem()
        line_item.set_tag(str(submission.exercise.id))
        try:
            ags.put_grade(grade, line_item)
        except LtiServiceException as exc:
            # At least Moodle sends a 409 when trying to save
            # a grade with same timestamp as an existing grade
            if exc.response.status_code == 409:
                logger.info("Grade for submission has already been saved through LTI; continuing")
            else:
                logger.exception(
                    "LTI Tool could not send grade to the Platform. "
                    "Tool user id: %s. Tool exercise id: %s. "
                    "Grade userId: %s. Grade timestamp: %s. "
                    "Line item id: %s. Line item tag: %s. ",
                    str(user.pk),
                    str(exercise.pk),
                    str(grade.get_user_id()),
                    str(grade.get_timestamp()),
                    str(line_item.get_id()),
                    str(line_item.get_tag()),
                )
