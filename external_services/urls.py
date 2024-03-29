from django.urls import path, re_path

from course.urls import INSTANCE_URL_PREFIX, EDIT_URL_PREFIX
from . import views


LTI_PREFIX = 'lti/'

urlpatterns = [
    re_path(INSTANCE_URL_PREFIX + r'external-link/(?P<menu_id>\d+)/$',
        views.ExternalLinkView.as_view(),
        name="external-service-link"),
    re_path(INSTANCE_URL_PREFIX + r'lti-login/(?P<menu_id>\d+)/$',
        views.LTILoginView.as_view(),
        name="lti-login"),
    re_path(EDIT_URL_PREFIX + r'menu/$',
        views.ListMenuItemsView.as_view(),
        name="external-services-list-menu"),
    re_path(EDIT_URL_PREFIX + r'menu/add/$',
        views.EditMenuItemView.as_view(),
        name="external-services-add-menu"),
    re_path(EDIT_URL_PREFIX + r'menu/(?P<menu_id>\d+)/edit/$',
        views.EditMenuItemView.as_view(),
        name="external-services-edit-menu"),
    re_path(EDIT_URL_PREFIX + r'menu/(?P<menu_id>\d+)/remove/$',
        views.RemoveMenuItemView.as_view(),
        name="external-services-remove-menu"),

    # LTI 1.3 routes
    path(LTI_PREFIX + 'auth_login/',
        views.LTI1p3AuthRequestView.as_view(),
        name="external-services-auth-login"),
    path(LTI_PREFIX + 'jwks',
        views.LTI1p3JwksView.as_view(),
        name="external-services-jwks"),
    path(LTI_PREFIX + 'token',
        views.LTI1p3TokenView.as_view(),
        name="external-services-token"),
]
