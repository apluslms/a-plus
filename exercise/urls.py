from django.conf.urls import url

from course.urls import INSTANCE_URL_PREFIX, EDIT_URL_PREFIX, USER_URL_PREFIX
from . import views, async_views, staff_views


EXERCISE_URL_PREFIX = INSTANCE_URL_PREFIX \
    + r'exercises/(?P<exercise_id>\d+)/'
SUBMISSION_URL_PREFIX = EXERCISE_URL_PREFIX \
    + r'submissions/(?P<submission_id>\d+)/'

urlpatterns = [
    url(USER_URL_PREFIX + r'$',
        views.profile, name="profile"),
    url(USER_URL_PREFIX + r'results/$',
        views.user_score, name="results"),
    url(EXERCISE_URL_PREFIX + r'$',
        views.view_exercise, name="exercise"),
    url(EXERCISE_URL_PREFIX + r'plain/$',
        views.view_exercise, { 'plain': True }, name="exercise-plain"),
    url(SUBMISSION_URL_PREFIX + r'$',
        views.view_submission, name="submission"),
    url(SUBMISSION_URL_PREFIX + r'poll/$',
        views.poll_submission, name="submission-poll"),
    url(SUBMISSION_URL_PREFIX \
            + r'file/(?P<file_id>\d+)/(?P<file_name>[\w\d\_\-\.]+)',
        views.view_submitted_file, name="submission-file"),

    url(r'^rest/exercise/(?P<exercise_id>\d+)/' \
            + r'students/(?P<student_ids>[\d\-]+)/(?P<hash_key>\w+)/$',
        async_views.new_async_submission, name="async-new"),
    url(r'^rest/submission/(?P<submission_id>\d+)/(?P<hash_key>\w+)/$',
        async_views.grade_async_submission, name="async-grade"),

    url(EXERCISE_URL_PREFIX + r'submissions/$',
        staff_views.list_exercise_submissions, name="submission-list"),
    url(EXERCISE_URL_PREFIX + r'submissions/create_and_assess/$',
        staff_views.create_and_assess_submission, name="submission-create"),
    url(SUBMISSION_URL_PREFIX + r'inspect/$',
        staff_views.inspect_exercise_submission, name="submission-inspect"),
    url(SUBMISSION_URL_PREFIX + r're-submit/$',
        staff_views.resubmit_to_service, name="submission-re-submit"),
    url(SUBMISSION_URL_PREFIX + r'assess/$',
        staff_views.assess_submission, name="submission-assess"),
    url(EDIT_URL_PREFIX + r'results/$',
        staff_views.results_table, name="all-results"),
    url(EDIT_URL_PREFIX + r'fetch-metadata/$',
        staff_views.fetch_exercise_metadata, name="exercise-metadata"),
    url(EDIT_URL_PREFIX + r'batch_create_and_assess/$',
        staff_views.batch_create_and_assess_submissions, name="batch-assess"),
]
