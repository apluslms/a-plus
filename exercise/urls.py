from django.conf.urls import patterns, url

from course.urls import INSTANCE_URL_PREFIX, EXERCISE_URL_PREFIX


SUBMISSION_URL_PREFIX = EXERCISE_URL_PREFIX + r'submissions/(?P<submission_id>\d+)/'

urlpatterns = patterns('exercise.views',
    url(INSTANCE_URL_PREFIX + r'user/$', 'profile'),
    url(INSTANCE_URL_PREFIX + r'user/results/$', 'user_score', name="user_score"),
    url(EXERCISE_URL_PREFIX + r'$', 'view_exercise', name="exercise"),
    url(EXERCISE_URL_PREFIX + r'plain/$', 'view_exercise', {'plain': True}),
    url(SUBMISSION_URL_PREFIX + r'$', 'view_submission', name="submission"),
    url(SUBMISSION_URL_PREFIX + r'file/(?P<file_id>\d+)/(?P<file_name>[\w\d\_\-\.]+)$',
        'view_submitted_file'),
    url(SUBMISSION_URL_PREFIX + r'poll/$', 'poll_submission'),
)
urlpatterns += patterns('exercise.async_views',
    url(r'^rest/exercise/(?P<exercise_id>\d+)/students/(?P<student_ids>[\d\-]+)/(?P<hash_key>\w+)/$',
        'new_async_submission'),
    url(r'^rest/submission/(?P<submission_id>\d+)/(?P<hash_key>\w+)/$',
        'grade_async_submission'),
)
urlpatterns += patterns('exercise.staff_views',
    url(INSTANCE_URL_PREFIX + r'teachers/results/$', 'results_table'),
    url(EXERCISE_URL_PREFIX + r'submissions/$', 'list_exercise_submissions'),
    url(SUBMISSION_URL_PREFIX + r'inspect/$', 'inspect_exercise_submission'),
    url(SUBMISSION_URL_PREFIX + r're-submit/$', 'resubmit_to_service'),
    url(SUBMISSION_URL_PREFIX + r'assess/$', 'assess_submission'),
    url(EXERCISE_URL_PREFIX + r'submissions/create_and_assess/$',
        'create_and_assess_submission'),
    url(INSTANCE_URL_PREFIX + r'teachers/batch_create_and_assess',
        'batch_create_and_assess_submissions'),    
    url(INSTANCE_URL_PREFIX + r'teachers/fetch-metadata/$',
        'fetch_exercise_metadata', name="exercise_metadata"),
)
