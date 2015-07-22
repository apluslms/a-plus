from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import TemplateView
import django.contrib.auth.views

import userprofile.views, course.views
import shibboleth_login.urls, userprofile.urls, course.urls, exercise.urls, \
    deviations.urls, external_services.urls, apps.urls, api.urls, \
    redirect_old_urls.urls


admin.autodiscover()

urlpatterns = [

    # Django
    url(r'^accounts/login/$', userprofile.views.login, name="login"),
    url(r'^accounts/logout/$', django.contrib.auth.views.logout,
        { "template_name": "aplus/logout.html" }, name="logout"),
    url(r'^admin/', include(admin.site.urls)),

    # Shibboleth
    url(r'^shibboleth/', include(shibboleth_login.urls)),

    # A+ - Pay attention to the order the URL patterns will be matched!
    url(r'^$', course.views.home, name='home'),
    url(r'^privacy-policy/$',
        TemplateView.as_view(template_name='aplus/privacy.html'),
        name="privacy_policy"),
    url(r'^api/', include(api.urls)),
    url(r'^apps/', include(apps.urls)),
    url(r'^external/', include(external_services.urls)),
    url(r'^', include(redirect_old_urls.urls)),
    url(r'^', include(userprofile.urls)),
    url(r'^', include(deviations.urls)),
    url(r'^', include(exercise.urls)),
    url(r'^', include(course.urls)),
]
