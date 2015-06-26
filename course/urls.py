from django.conf.urls import patterns, url


COURSE_URL_PREFIX = r'^(?P<course_url>[\w\d\-\.]+)/'
INSTANCE_URL_PREFIX = COURSE_URL_PREFIX + r'(?P<instance_url>[\w\d\-\.]+)/'
MODULE_URL_PREFIX = INSTANCE_URL_PREFIX + r'(?P<module_url>[\w\d\-\.]+)/'
EXERCISE_URL_PREFIX = INSTANCE_URL_PREFIX + r'exercises/(?P<exercise_id>\d+)/'

urlpatterns = patterns('course.teacher_views',
    url(INSTANCE_URL_PREFIX + r'teachers/$', 'edit_course'),

    url(INSTANCE_URL_PREFIX + r'teachers/add-module/$', 'add_or_edit_module'),
    url(MODULE_URL_PREFIX + r'edit/$', 'add_or_edit_module'),
    url(MODULE_URL_PREFIX + r'delete/$', 'remove_module'),

    url(MODULE_URL_PREFIX + r'add-exercise/$', 'add_or_edit_exercise'),
    url(MODULE_URL_PREFIX + r'add-exercise/(?P<exercise_type>[\w\d\-\_]+)/$',
        'add_or_edit_exercise'),
    url(EXERCISE_URL_PREFIX + r'edit/$', 'add_or_edit_exercise'),
    url(EXERCISE_URL_PREFIX + r'delete/$', 'remove_exercise'),
)
urlpatterns += patterns('course.views',
    url(r'archive/$', 'course_archive'),
    url(COURSE_URL_PREFIX + r'$', 'view_course'),
    url(INSTANCE_URL_PREFIX + r'$', 'view_instance', name="course"),
    url(MODULE_URL_PREFIX + r'$', 'view_module'),
    url(INSTANCE_URL_PREFIX + r'user/export-calendar/$', 'export_calendar'),
    url(INSTANCE_URL_PREFIX + r'user/filter-categories/$', 'filter_categories'),
)
