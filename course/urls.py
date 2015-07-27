from django.conf.urls import url

from . import views


COURSE_URL_PREFIX = r'^(?P<course>[\w\d\-\.]+)/'
INSTANCE_URL_PREFIX = COURSE_URL_PREFIX + r'(?P<instance>[\w\d\-\.]+)/'
EDIT_URL_PREFIX = INSTANCE_URL_PREFIX + r'teachers/'
USER_URL_PREFIX = INSTANCE_URL_PREFIX + r'user/'

urlpatterns = [
    url(r'^$',
        views.HomeView.as_view(),
        name='home'),
    url(r'^archive/$',
        views.ArchiveView.as_view(),
        name="archive"),
    url(COURSE_URL_PREFIX + r'$',
        views.CourseView.as_view(),
        name="course-instances"),
    url(INSTANCE_URL_PREFIX + r'$',
        views.InstanceView.as_view(),
        name="course"),
    url(USER_URL_PREFIX + r'export-calendar/$',
        views.CalendarExport.as_view(),
        name='export-calendar'),
    url(USER_URL_PREFIX + r'filter-categories/$',
        views.FilterCategories.as_view(),
        name='filter-categories'),
    url(INSTANCE_URL_PREFIX + r'(?P<module>[\w\d\-\.]+)/$',
        views.ModuleView.as_view(),
        name="module"),
    url(INSTANCE_URL_PREFIX
            + r'(?P<module>[\w\d\-\.]+)/(?P<chapter>[\w\d\-\.]+)/$',
        views.ChapterView.as_view(),
        name="chapter"),
]
