from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include
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
    path('', include(shibboleth_login.urls)),
    path('', include(social_django.urls, namespace='social')),
    re_path(r'^api/v(?P<version>(2))/', include(api.urls_v2)), # why version in url? doc/api_versioning.md
    path('accounts/', include(userprofile.urls)),
    path('diploma/', include(diploma.urls)),
    path('', include(redirect_old_urls.urls)),
    path('', include(apps.urls)),
    path('', include(news.urls)),
    path('', include(external_services.urls)),
    path('', include(course.long_urls)),
    path('', include(deviations.urls)),
    path('', include(edit_course.urls)),
    path('', include(notification.urls)),
    path('', include(lti_tool.urls)),
    path('', include(exercise.urls)),
    path('', include(course.urls)),
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
