from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'create/(?P<coursediploma_id>\d+)/(?P<userprofile_id>\d+)$',
        views.CreateDiploma.as_view(),
        name="diploma-create"),
    url(r'(?P<diploma_hash>[a-f0-9]{32})/$',
        views.ViewDiploma.as_view(),
        name="diploma-view"),
    #TODO list view for all student grades
]
