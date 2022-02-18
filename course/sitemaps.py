from django.contrib import sitemaps
from django.urls.base import reverse
from django.utils import timezone

from lib.sitemaps import AplusSitemap
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


class InstanceSitemap(AplusSitemap):
    changefreq = 'daily'
    base_priority = 0.4

    def items(self):
        return CourseInstance.objects.filter(
            view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            visible_to_students=True,
        )


class ModuleSitemap(AplusSitemap):
    changefreq = 'daily'
    base_priority = 0.2

    def items(self):
        return CourseModule.objects.filter(
            course_instance__view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            course_instance__visible_to_students=True,
            opening_time__lte=timezone.now(),
        )


all_sitemaps = {
    'course_static': CourseStaticViewSitemap,
    'course_instance': InstanceSitemap,
    'course_module': ModuleSitemap,
}
