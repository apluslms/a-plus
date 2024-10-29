from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, re_path

from . import views
import shibboleth_login.urls
import social_django.urls
import userprofile.sitemaps
import userprofile.urls
import course.long_urls
import course.sitemaps
import course.urls
import exercise.sitemaps
import exercise.urls
import edit_course.urls
import deviations.urls
import notification.urls
import external_services.urls
import news.urls
import diploma.urls
import apps.urls
import api.urls_v2
import redirect_old_urls.urls
import lti_tool.urls


admin.autodiscover()

all_sitemaps = {
    **course.sitemaps.all_sitemaps,
    **exercise.sitemaps.all_sitemaps,
    **userprofile.sitemaps.all_sitemaps,
}

#  Pay attention to the order the URL patterns will be matched!
urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^', include(shibboleth_login.urls)),
    re_path('', include(social_django.urls, namespace='social')),
    re_path(r'^api/v(?P<version>(2))/', include(api.urls_v2)), # why version in url? doc/api_versioning.md
    re_path(r'^accounts/', include(userprofile.urls)),
    re_path(r'^diploma/', include(diploma.urls)),
    re_path(r'^', include(redirect_old_urls.urls)),
    re_path(r'^', include(apps.urls)),
    re_path(r'^', include(news.urls)),
    re_path(r'^', include(external_services.urls)),
    re_path(r'^', include(course.long_urls)),
    re_path(r'^', include(deviations.urls)),
    re_path(r'^', include(edit_course.urls)),
    re_path(r'^', include(notification.urls)),
    re_path(r'^', include(lti_tool.urls)),
    re_path(r'^', include(exercise.urls)),
    re_path(r'^', include(course.urls)),
    path('sitemap.xml', sitemap, { 'sitemaps': all_sitemaps },
        name='django.contrib.sitemaps.views.sitemap'),
]

handler403 = views.error_403
handler404 = views.error_404
handler500 = views.error_500

if settings.DEBUG:
    import django.views.static
    urlpatterns.insert(0, re_path(r'^media/(?P<path>.*)$', django.views.static.serve,
        { 'document_root': settings.MEDIA_ROOT }))


if settings.ENABLE_DJANGO_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns.insert(
        0,
        path('__debug__/', include(debug_toolbar.urls)),
    )
