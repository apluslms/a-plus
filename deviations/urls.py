from django.conf.urls import patterns, url

from course.urls import EDIT_URL_PREFIX


urlpatterns = patterns('deviations.teacher_views',
    url(EDIT_URL_PREFIX + r'deviations/$', 'list_dl_deviations'),
    url(EDIT_URL_PREFIX + r'deviations/add/$', 'add_dl_deviations'),
    url(EDIT_URL_PREFIX + r'deviations/(?P<deviation_id>\d+)/remove/$',
        'remove_dl_deviation'),
)
