from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'list/(?P<coursediploma_id>\d+)/$',
        views.DiplomaListView.as_view(),
        name="diploma-list"),
    url(r'create/(?P<coursediploma_id>\d+)/(?P<userprofile_id>\d+)/$',
        views.DiplomaCreateView.as_view(),
        name="diploma-create"),
    url(r'(?P<diploma_hash>[a-f0-9]{32})/$',
        views.DiplomaPdfView.as_view(),
        name="diploma-view"),
]
