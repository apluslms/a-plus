from django.contrib import sitemaps
from django.urls.base import reverse
from django.utils import timezone

from course.models import CourseInstance
from .models import BaseExercise, CourseChapter, LearningObject


class BaseExerciseSitemap(sitemaps.Sitemap):
    priority = 0.2
    changefreq = 'daily'

    def items(self):
        return BaseExercise.objects.filter(
            course_module__course_instance__view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            course_module__opening_time__lte=timezone.now(),
            status__in=[LearningObject.STATUS.READY, LearningObject.STATUS.UNLISTED],
            audience=LearningObject.AUDIENCE.COURSE_AUDIENCE,
        )

    def location(self, item):
        return item.get_display_url()


class CourseChapterSitemap(sitemaps.Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return CourseChapter.objects.filter(
            course_module__course_instance__view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            course_module__opening_time__lte=timezone.now(),
            status__in=[LearningObject.STATUS.READY, LearningObject.STATUS.UNLISTED],
            audience=LearningObject.AUDIENCE.COURSE_AUDIENCE,
        )

    def location(self, item):
        return item.get_display_url()


class TableOfContentsSitemap(sitemaps.Sitemap):
    priority = 0.2
    changefreq = 'monthly'

    def items(self):
        return CourseInstance.objects.filter(
            view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
        )

    def location(self, item):
        return reverse('toc', kwargs=item.get_url_kwargs())


all_sitemaps = {
    'exercise_exercise': BaseExerciseSitemap,
    'exercise_chapter': CourseChapterSitemap,
    'exercise_toc': TableOfContentsSitemap,
}
