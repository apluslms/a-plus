from django.conf.urls import patterns, url

from course.urls import INSTANCE_URL_PREFIX


urlpatterns = patterns('deviations.teacher_views',
    url(INSTANCE_URL_PREFIX + r'teachers/deviations/$',
        'list_dl_deviations'),
    url(INSTANCE_URL_PREFIX + r'teachers/deviations/add/$',
        'add_dl_deviations'),
    url(INSTANCE_URL_PREFIX + r'teachers/deviations/remove/(?P<deviation_id>\d+)/$',
        'remove_dl_deviation'),
)
