from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [
    path('list/<int:coursediploma_id>/',
        views.DiplomaListView.as_view(),
        name="diploma-list"),
    path('create/<int:coursediploma_id>/<int:userprofile_id>/',
        views.DiplomaCreateView.as_view(),
        name="diploma-create"),
    re_path(r'(?P<diploma_hash>[a-f0-9]{32})/$',
        views.DiplomaPdfView.as_view(),
        name="diploma-view"),
]
