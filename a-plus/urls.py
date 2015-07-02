from django.conf import settings
from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.views.generic import TemplateView


admin.autodiscover()

urlpatterns = patterns('',

    # Django
    url(r'^accounts/login/$', 'userprofile.views.login'),
    url(r'^accounts/logout/$', "django.contrib.auth.views.logout",
        { "template_name": "aplus/logout.html" }, name="logout"),
    url(r'^admin/', include(admin.site.urls)),

    # Shibboleth
    url(r'^shibboleth/', include('shibboleth_login.urls')),

    # A+ - Pay attention to the order the URL patterns will be matched!
    url(r'^$', 'course.views.home'),
    url(r'^privacy-policy$', TemplateView.as_view(template_name='aplus/privacy.html'),
        name="privacy_policy"),
    url(r'^api/', include('api.urls')),
    url(r'^apps/', include('apps.urls')),
    url(r'^external/', include('external_services.urls')),
    url(r'^', include('redirect_old_urls.urls')),
    url(r'^', include('userprofile.urls')),
    url(r'^', include('exercise.urls')),
    url(r'^', include('course.urls')),
    url(r'^', include('deviations.urls')),
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
