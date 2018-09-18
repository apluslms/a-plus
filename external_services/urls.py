from django.conf.urls import url

from course.urls import INSTANCE_URL_PREFIX, EDIT_URL_PREFIX
from . import views


urlpatterns = [
    url(INSTANCE_URL_PREFIX + r'external-link/(?P<menu_id>\d+)/$',
        views.ExternalLinkView.as_view(),
        name="external-service-link"),
    url(INSTANCE_URL_PREFIX + r'lti-login/(?P<menu_id>\d+)/$',
        views.LTILoginView.as_view(),
        name="lti-login"),
    url(EDIT_URL_PREFIX + r'menu/$',
        views.ListMenuItemsView.as_view(),
        name="external-services-list-menu"),
    url(EDIT_URL_PREFIX + r'menu/add/$',
        views.EditMenuItemView.as_view(),
        name="external-services-add-menu"),
    url(EDIT_URL_PREFIX + r'menu/(?P<menu_id>\d+)/edit/$',
        views.EditMenuItemView.as_view(),
        name="external-services-edit-menu"),
    url(EDIT_URL_PREFIX + r'menu/(?P<menu_id>\d+)/remove/$',
        views.RemoveMenuItemView.as_view(),
        name="external-services-remove-menu"),
]
