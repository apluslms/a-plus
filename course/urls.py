from django.conf.urls import url

from course import views, teacher_views


COURSE_URL_PREFIX = r'^(?P<course_url>[\w\d\-\.]+)/'
INSTANCE_URL_PREFIX = COURSE_URL_PREFIX + r'(?P<instance_url>[\w\d\-\.]+)/'
EDIT_URL_PREFIX = INSTANCE_URL_PREFIX + r'teachers/'
USER_URL_PREFIX = INSTANCE_URL_PREFIX + r'user/'

urlpatterns = [
    url(r'^archive/$', views.course_archive, name="archive"),
    url(COURSE_URL_PREFIX + r'$', views.view_course, name="course-instances"),
    url(INSTANCE_URL_PREFIX + r'$', views.view_instance, name="course"),

    url(USER_URL_PREFIX + r'export-calendar/$',
        views.export_calendar, name='export-calendar'),
    url(USER_URL_PREFIX + r'filter-categories/$',
        views.filter_categories, name='filter-categories'),

    url(EDIT_URL_PREFIX + r'$',
        teacher_views.edit_course, name='edit-course'),

    url(EDIT_URL_PREFIX + r'module/add/$',
        teacher_views.add_or_edit_module, name='add-module'),
    url(EDIT_URL_PREFIX + r'module/(?P<module_id>\d+)/$',
        teacher_views.add_or_edit_module, name='edit-module'),
    url(EDIT_URL_PREFIX + r'module/(?P<module_id>\d+)/delete/$',
        teacher_views.remove_module, name='remove-module'),

    url(EDIT_URL_PREFIX + r'module/(?P<module_id>\d+)/add-exercise/$',
        teacher_views.add_or_edit_exercise, name='add-exercise'),
    url(EDIT_URL_PREFIX + r'module/(?P<module_id>\d+)/add-exercise/'
            + r'(?P<exercise_type>[\w\d\-\_]+)/$',
        teacher_views.add_or_edit_exercise, name='add-exercise-type'),
    url(EDIT_URL_PREFIX + r'exercise/(?P<exercise_id>\d+)/$',
        teacher_views.add_or_edit_exercise, name='edit-exercise'),
    url(EDIT_URL_PREFIX + r'exercise/(?P<exercise_id>\d+)/delete/$',
        teacher_views.remove_exercise, name='remove-exercise'),

    url(INSTANCE_URL_PREFIX + r'(?P<module_url>[\w\d\-\.]+)/$',
        views.view_module, name="module"),
    url(INSTANCE_URL_PREFIX
            + r'(?P<module_url>[\w\d\-\.]+)/(?P<chapter_url>[\w\d\-\.]+)$',
        views.view_chapter, name="chapter"),
]
