from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin

import shibboleth_login.urls, social.apps.django_app.urls, \
    userprofile.urls, course.urls, course.long_urls, \
    exercise.urls, edit_course.urls, deviations.urls, notification.urls, \
    external_services.urls, apps.urls, api.urls, redirect_old_urls.urls


admin.autodiscover()

#  Pay attention to the order the URL patterns will be matched!
urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^shibboleth/', include(shibboleth_login.urls)),
    url('', include(social.apps.django_app.urls, namespace='social')),
    url(r'^api/', include(api.urls)), # ^api/v1/ only
    url(r'^accounts/', include(userprofile.urls)),
    url(r'^', include(redirect_old_urls.urls)),
    url(r'^', include(apps.urls)),
    url(r'^', include(external_services.urls)),
    url(r'^', include(deviations.urls)),
    url(r'^', include(edit_course.urls)),
    url(r'^', include(notification.urls)),
    url(r'^', include(course.long_urls)),
    url(r'^', include(exercise.urls)),
    url(r'^', include(course.urls)),
]

if settings.DEBUG:
    import django.views.static
    urlpatterns.insert(0, url(r'^media/(?P<path>.*)$', django.views.static.serve,
        { 'document_root': settings.MEDIA_ROOT }))
