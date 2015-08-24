from django.conf.urls import url

from course.urls import EDIT_URL_PREFIX
from . import views


MODEL_URL_PREFIX = EDIT_URL_PREFIX + r'(?P<model>[\w\d\-]+)/'

urlpatterns = [
    url(EDIT_URL_PREFIX + r'$',
        views.EditCourseView.as_view(),
        name='course-edit'),
    url(EDIT_URL_PREFIX + r'batch-assess/$',
        views.EditCourseView.as_view(template_name='edit_course/batch_assess.html'),
        name='batch-assess-form'),
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
]
