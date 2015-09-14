from django.conf.urls import url

from course.urls import INSTANCE_URL_PREFIX, USER_URL_PREFIX, EDIT_URL_PREFIX
from . import views, async_views, staff_views


EXERCISE_URL_PREFIX = INSTANCE_URL_PREFIX \
    + r'exercises/(?P<exercise_id>\d+)/'
SUBMISSION_URL_PREFIX = EXERCISE_URL_PREFIX \
    + r'submissions/(?P<submission_id>\d+)/'

urlpatterns = [
    url(USER_URL_PREFIX + r'results/$',
        views.ResultsView.as_view(),
        name="results"),
    url(EXERCISE_URL_PREFIX + r'$',
        views.ExerciseView.as_view(),
        name="exercise"),
    url(EXERCISE_URL_PREFIX + r'plain/$',
        views.ExerciseView.as_view(
            force_ajax_template=True, post_url_name="exercise-plain"),
        name="exercise-plain"),
    url(EXERCISE_URL_PREFIX + r'info/$',
        views.ExerciseInfoView.as_view(),
        name="exercise-info"),
    url(SUBMISSION_URL_PREFIX + r'$',
        views.SubmissionView.as_view(),
        name="submission"),
    url(SUBMISSION_URL_PREFIX + r'plain/$',
        views.SubmissionView.as_view(force_ajax_template=True),
        name="submission-plain"),
    url(SUBMISSION_URL_PREFIX + r'poll/$',
        views.SubmissionPollView.as_view(),
        name="submission-poll"),
    url(SUBMISSION_URL_PREFIX \
            + r'file/(?P<file_id>\d+)/(?P<file_name>[\w\d\_\-\.]+)',
        views.SubmittedFileView.as_view(),
        name="submission-file"),

    url(r'^rest/exercise/(?P<exercise_id>\d+)/' \
            + r'students/(?P<student_ids>[\d\-]+)/(?P<hash_key>\w+)/$',
        async_views.new_async_submission,
        name="async-new"),
    url(r'^rest/submission/(?P<submission_id>\d+)/(?P<hash_key>\w+)/$',
        async_views.grade_async_submission,
        name="async-grade"),

    url(EXERCISE_URL_PREFIX + r'submissions/$',
        staff_views.ListSubmissionsView.as_view(),
        name="submission-list"),
    url(EXERCISE_URL_PREFIX + r'submissions/create_and_assess/$',
        staff_views.CreateSubmissionView.as_view(),
        name="submission-create"),
    url(SUBMISSION_URL_PREFIX + r'inspect/$',
        staff_views.InspectSubmissionView.as_view(),
        name="submission-inspect"),
    url(SUBMISSION_URL_PREFIX + r're-submit/$',
        staff_views.ResubmitSubmissionView.as_view(),
        name="submission-re-submit"),
    url(SUBMISSION_URL_PREFIX + r'assess/$',
        staff_views.AssessSubmissionView.as_view(),
        name="submission-assess"),
    url(EDIT_URL_PREFIX + r'results/$',
        staff_views.AllResultsView.as_view(),
        name="all-results"),
    url(EDIT_URL_PREFIX + r'fetch-metadata/$',
        staff_views.FetchMetadataView.as_view(),
        name="exercise-metadata"),
]
