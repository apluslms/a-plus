from django.conf.urls.defaults import *
from oembed.views import get_oembed

urlpatterns = patterns('',
    (r'^$', get_oembed),
)
