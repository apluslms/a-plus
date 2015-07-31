from django.conf.urls import url, include
from django.contrib import admin

import shibboleth_login.urls, userprofile.urls, course.urls, exercise.urls, \
    edit_course.urls, deviations.urls, external_services.urls, apps.urls, \
    api.urls, redirect_old_urls.urls


admin.autodiscover()

#  Pay attention to the order the URL patterns will be matched!
urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^shibboleth/', include(shibboleth_login.urls)),
    url(r'^api/', include(api.urls)),
    url(r'^accounts/', include(userprofile.urls)),
    url(r'^', include(redirect_old_urls.urls)),
    url(r'^', include(apps.urls)),
    url(r'^', include(external_services.urls)),
    url(r'^', include(edit_course.urls)),
    url(r'^', include(deviations.urls)),
    url(r'^', include(exercise.urls)),
    url(r'^', include(course.urls)),
]
