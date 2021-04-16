from django.contrib import sitemaps
from django.urls.base import reverse
from django.utils import timezone

from .models import CourseInstance, CourseModule


class CourseStaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return [
            'home',
            'archive',
        ]

    def location(self, item):
        return reverse(item)


class InstanceSitemap(sitemaps.Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return CourseInstance.objects.filter(
            view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
        )

    def location(self, item):
        return item.get_display_url()


class ModuleSitemap(sitemaps.Sitemap):
    priority = 0.2
    changefreq = 'daily'

    def items(self):
        return CourseModule.objects.filter(
            course_instance__view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            opening_time__lte=timezone.now(),
        )

    def location(self, item):
        return item.get_display_url()


all_sitemaps = {
    'course_static': CourseStaticViewSitemap,
    'course_instance': InstanceSitemap,
    'course_module': ModuleSitemap,
}
