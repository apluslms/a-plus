# A+
from views import login, home, privacy

# Django
from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',

    # A+
    (r'^$', home),
    url(r'^privacy-policy(?:.html)?$', privacy, name="privacy_policy"),

    (r'^exercise/', include('exercise.urls')),
    (r'^course/', include('course.urls')),
    (r'^api/', include('api_urls')),
    (r'^userprofile/', include('userprofile.urls')),
    (r'^apps/', include('apps.urls')),
    (r'^external/', include('external_services.urls')),

    # Shibboleth
    (r'^shibboleth/', include('django_shibboleth.urls')),

    # Django:
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/login/$', login),
    url(r'^accounts/logout/$', "django.contrib.auth.views.logout",
        { "template_name": "aaltoplus/logout.html" }, name="logout"),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
        url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.STATIC_ROOT,
        }),
    )
