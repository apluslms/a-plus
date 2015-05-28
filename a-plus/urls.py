from django.conf import settings
from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.views.generic import TemplateView


admin.autodiscover()

urlpatterns = patterns('',

    # A+
    url(r'^privacy-policy$', TemplateView.as_view(template_name='aaltoplus/privacy.html'),
        name="privacy_policy"),
    (r'^$', 'course.views.home'),
    (r'^exercise/', include('exercise.urls')),
    (r'^course/', include('course.urls')),
    (r'^api/', include('api.urls')),
    (r'^userprofile/', include('userprofile.urls')),
    (r'^apps/', include('apps.urls')),
    (r'^external/', include('external_services.urls')),

    # Shibboleth
    (r'^shibboleth/', include('django_shibboleth.urls')),

    # Django
    (r'^accounts/login/$', 'userprofile.views.login'),
    url(r'^accounts/logout/$', "django.contrib.auth.views.logout",
        { "template_name": "aaltoplus/logout.html" }, name="logout"),
    (r'^admin/', include(admin.site.urls)),
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
