import logging

from django.conf import settings
from django.contrib.auth.models import User
from pylti1p3.grade import Grade
from pylti1p3.contrib.django import DjangoMessageLaunch, DjangoCacheDataStorage, DjangoDbToolConf
from pylti1p3.lineitem import LineItem
from pylti1p3.exception import LtiException, LtiServiceException

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

def send_lti_points(request, submission):
    from exercise.cache.points import SubmittableExerciseEntry # pylint: disable=import-outside-toplevel
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
        entry = SubmittableExerciseEntry.get(exercise, user)
        best_submission = entry.best_submission
        if best_submission is None:
            return
        ags = launch.get_ags()
        grade = Grade()
        (grade.set_score_given(best_submission.points)
            .set_timestamp(best_submission.date.strftime('%Y-%m-%dT%H:%M:%S+0000'))
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
                raise exc
