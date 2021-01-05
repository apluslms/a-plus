from django.conf.urls import url

from . import views


COURSE_URL_PREFIX = r'^(?P<course_slug>[\w\d\-\.]+)/'
INSTANCE_URL_PREFIX = COURSE_URL_PREFIX + r'(?P<instance_slug>[\w\d\-\.]+)/'
EDIT_URL_PREFIX = INSTANCE_URL_PREFIX + r'teachers/'
USER_URL_PREFIX = INSTANCE_URL_PREFIX + r'user/'
MODULE_URL_PREFIX = INSTANCE_URL_PREFIX + r'(?P<module_slug>[\w\d\-\.]+)/'

urlpatterns = [
    url(r'^$',
        views.HomeView.as_view(),
        name='home'),
    url(r'^archive/$',
        views.ArchiveView.as_view(),
        name="archive"),
    url(COURSE_URL_PREFIX + r'instances/$',
        views.CourseInstancesView.as_view(),
        name="course_instances"),
    url(COURSE_URL_PREFIX + r'$',
        views.LastInstanceView.as_view(),
        name="course_last_instance"),
    url(INSTANCE_URL_PREFIX + r'$',
        views.InstanceView.as_view(),
        name="course"),
    url(MODULE_URL_PREFIX + r'$',
        views.ModuleView.as_view(),
        name="module"),
]
