from django.conf.urls import url

from .urls import USER_URL_PREFIX, EDIT_URL_PREFIX
from . import views, staff_views

# These need to be listed before the exercise URL routings.
urlpatterns = [
    url(USER_URL_PREFIX + r'enroll/$',
        views.Enroll.as_view(),
        name='enroll'),
    url(USER_URL_PREFIX + r'export-calendar/$',
        views.CalendarExport.as_view(),
        name='export-calendar'),
    # url(USER_URL_PREFIX + r'filter-categories/$',
    #     views.FilterCategories.as_view(),
    #     name='filter-categories'),
    url(USER_URL_PREFIX + r'groups/$',
        views.GroupsView.as_view(),
        name="groups"),
    url(USER_URL_PREFIX + r'groups/select/$',
        views.GroupSelect.as_view(),
        name="group-select"),
    url(EDIT_URL_PREFIX + r'participants/$',
        staff_views.ParticipantsView.as_view(),
        name="participants"),
    url(EDIT_URL_PREFIX + r'groups/$',
        staff_views.GroupsView.as_view(),
        name="groups-list"),
    url(EDIT_URL_PREFIX + r'groups/new/$',
        staff_views.GroupsEditView.as_view(),
        name="groups-add"),
    url(EDIT_URL_PREFIX + r'groups/(?P<group_id>\d+)/$',
        staff_views.GroupsEditView.as_view(),
        name="groups-edit"),
    url(EDIT_URL_PREFIX + r'groups/(?P<group_id>\d+)/delete/$',
        staff_views.GroupsDeleteView.as_view(),
        name="groups-delete"),
]
