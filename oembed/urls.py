from django.conf.urls import patterns
from oembed.views import get_oembed

urlpatterns = patterns('',
    (r'^$', get_oembed),
)
