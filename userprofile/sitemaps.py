from django.contrib import sitemaps
from django.urls.base import reverse


class UserProfileStaticViewSitemap(sitemaps.Sitemap):
    priority = 0.1
    changefreq = 'yearly'

    def items(self):
        return [
            'privacy_notice',
            'accessibility_statement',
            'support_channels',
        ]

    def location(self, item):
        return reverse(item)


all_sitemaps = {
    'userprofile_static': UserProfileStaticViewSitemap,
}
