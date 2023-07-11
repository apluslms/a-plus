from django.urls import re_path

from course.urls import EDIT_URL_PREFIX
from . import views


urlpatterns = [
    re_path(EDIT_URL_PREFIX + r'news/$',
        views.ListNewsView.as_view(),
        name="news-list"),
    re_path(EDIT_URL_PREFIX + r'news/add/$',
        views.EditNewsView.as_view(),
        name="news-add"),
    re_path(EDIT_URL_PREFIX + r'news/(?P<news_id>\d+)/edit/$',
        views.EditNewsView.as_view(),
        name="news-edit"),
    re_path(EDIT_URL_PREFIX + r'news/(?P<news_id>\d+)/remove/$',
        views.RemoveNewsView.as_view(),
        name="news-remove"),
]
