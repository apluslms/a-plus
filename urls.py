# A+
from views import login, home, privacy, verify_credentials
from oauth_provider.views import protected_resource_example

# Django
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    # OAuth plus
    url(r'^oauth/', include('oauth_provider.urls')),
    url(r'^oauth/photo/$', protected_resource_example, name='oauth_example'),
    
    # A view for returning credentials through OAuth authentication
    url(r'^account/verify_credentials.json$', verify_credentials),
    
    # A+
    (r'^$', home),
    (r'^privacy-policy(?:.html)?$', privacy),
    
    (r'^exercise/', include('exercise.urls')),
    (r'^course/', include('course.urls')),
    (r'^api/', include('api_urls')),
    (r'^userprofile/', include('userprofile.urls')),
    (r'^apps/', include('apps.urls')),
    
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    
    # Shibboleth
    (r'^shibboleth/', include('django_shibboleth.urls')),
    
    # Django:
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/login/$', login),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'template_name': 'aaltoplus/logout.html'}),
)

urlpatterns += patterns('',
    (r'^comments/', include('django.contrib.comments.urls')),
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
