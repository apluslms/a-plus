from django.conf.urls import url

from course.urls import EDIT_URL_PREFIX
from . import views


MODEL_URL_PREFIX = EDIT_URL_PREFIX + r'(?P<model>[\w\d\-]+)/'

urlpatterns = [
    url(EDIT_URL_PREFIX + r'course/$',
        views.EditInstanceView.as_view(),
        name='course-details'),
    url(EDIT_URL_PREFIX + r'$',
        views.EditContentView.as_view(),
        name='course-edit'),
    url(MODEL_URL_PREFIX + r'add/$',
        views.ModelEditView.as_view(),
        name='model-create'),
    url(MODEL_URL_PREFIX + r'add/(?P<parent_id>\d+)/$',
        views.ModelEditView.as_view(),
        name='model-create-for'),
    url(MODEL_URL_PREFIX + r'add/(?P<parent_id>\d+)/(?P<type>[\w\d\-]+)/$',
        views.ModelEditView.as_view(),
        name='model-create-type-for'),
    url(MODEL_URL_PREFIX + r'(?P<id>\d+)/$',
        views.ModelEditView.as_view(),
        name='model-edit'),
    url(MODEL_URL_PREFIX + r'(?P<id>\d+)/delete/$',
        views.ModelDeleteView.as_view(),
        name='model-remove'),
    url(EDIT_URL_PREFIX + r'batch-assess/$',
        views.BatchCreateSubmissionsView.as_view(),
        name='batch-assess'),
    url(EDIT_URL_PREFIX + r'course/clone/$',
        views.CloneInstanceView.as_view(),
        name='course-clone'),
]
