from django.urls import re_path

from . import views


COURSE_URL_PREFIX = r'^(?P<course_slug>[\w\d\-\.]+)/'
INSTANCE_URL_PREFIX = COURSE_URL_PREFIX + r'(?P<instance_slug>[\w\d\-\.]+)/'
EDIT_URL_PREFIX = INSTANCE_URL_PREFIX + r'teachers/'
USER_URL_PREFIX = INSTANCE_URL_PREFIX + r'user/'
MODULE_URL_PREFIX = INSTANCE_URL_PREFIX + r'(?P<module_slug>[\w\d\-\.]+)/'

urlpatterns = [
    re_path(r'^$',
        views.HomeView.as_view(),
        name='home'),
    re_path(r'^archive/$',
        views.ArchiveView.as_view(),
        name="archive"),
    re_path(COURSE_URL_PREFIX + r'instances/$',
        views.CourseInstancesView.as_view(),
        name="course_instances"),
    re_path(COURSE_URL_PREFIX + r'$',
        views.LastInstanceView.as_view(),
        name="course_last_instance"),
    re_path(INSTANCE_URL_PREFIX + r'$',
        views.InstanceView.as_view(),
        name="course"),
    re_path(MODULE_URL_PREFIX + r'$',
        views.ModuleView.as_view(),
        name="module"),
]
