from django.conf.urls import url

from course.urls import EDIT_URL_PREFIX
from . import views


urlpatterns = [
    url(EDIT_URL_PREFIX + r'news/$',
        views.ListNewsView.as_view(),
        name="news-list"),
    url(EDIT_URL_PREFIX + r'news/add/$',
        views.EditNewsView.as_view(),
        name="news-add"),
    url(EDIT_URL_PREFIX + r'news/(?P<news_id>\d+)/edit/$',
        views.EditNewsView.as_view(),
        name="news-edit"),
    url(EDIT_URL_PREFIX + r'news/(?P<news_id>\d+)/remove/$',
        views.RemoveNewsView.as_view(),
        name="news-remove"),
]
