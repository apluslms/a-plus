from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'list/(?P<coursediploma_id>\d+)/$',
        views.DiplomaListView.as_view(),
        name="diploma-list"),
    re_path(r'create/(?P<coursediploma_id>\d+)/(?P<userprofile_id>\d+)/$',
        views.DiplomaCreateView.as_view(),
        name="diploma-create"),
    re_path(r'(?P<diploma_hash>[a-f0-9]{32})/$',
        views.DiplomaPdfView.as_view(),
        name="diploma-view"),
]
