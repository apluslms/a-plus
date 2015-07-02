from django.conf.urls import patterns, url

urlpatterns = patterns('shibboleth_login.views',
    url(r'^login/$', 'login'),
    url(r'^debug/$', 'debug'),
)
