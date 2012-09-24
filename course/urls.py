from django.conf.urls.defaults import *
from course.views import view_course, view_instance, view_instance_results, view_instance_calendar,\
    view_my_page, add_or_edit_module, teachers_view, course_archive, assistants_view

COURSE_URL_PREFIX = r'^(?P<course_url>[\w\d\-\.]+)/'
INSTANCE_URL_PREFIX = COURSE_URL_PREFIX + r'(?P<instance_url>[\w\d\-\.]+)/'

urlpatterns = patterns('',
    (r'archive/$', course_archive),
    (COURSE_URL_PREFIX + r'$', view_course),
    (INSTANCE_URL_PREFIX + r'$', view_instance),
    (INSTANCE_URL_PREFIX + r'results/$', view_instance_results),
    (INSTANCE_URL_PREFIX + r'me/$', view_my_page),
    (INSTANCE_URL_PREFIX + r'calendar/$', view_instance_calendar),
    (INSTANCE_URL_PREFIX + r'teachers/$', teachers_view),
    (INSTANCE_URL_PREFIX + r'assistants/$', assistants_view),
    (INSTANCE_URL_PREFIX + r'modules/$', add_or_edit_module),
    (INSTANCE_URL_PREFIX + r'modules/(?P<module_id>\d+)/$', add_or_edit_module),
)
