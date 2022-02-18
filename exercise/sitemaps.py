from django.urls.base import reverse
from django.utils import timezone

from course.models import CourseInstance
from lib.sitemaps import AplusSitemap
from .models import BaseExercise, CourseChapter, LearningObject


class BaseExerciseSitemap(AplusSitemap):
    changefreq = 'daily'
    base_priority = 0.5

    def items(self):
        return BaseExercise.objects.filter(
            course_module__course_instance__view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            course_module__course_instance__visible_to_students=True,
            course_module__opening_time__lte=timezone.now(),
            status=LearningObject.STATUS.READY,
            audience=LearningObject.AUDIENCE.COURSE_AUDIENCE,
            parent__isnull=True,
        )


class CourseChapterSitemap(AplusSitemap):
    changefreq = 'daily'

    def items(self):
        return CourseChapter.objects.filter(
            course_module__course_instance__view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            course_module__course_instance__visible_to_students=True,
            course_module__opening_time__lte=timezone.now(),
            status__in=[LearningObject.STATUS.READY, LearningObject.STATUS.UNLISTED],
            audience=LearningObject.AUDIENCE.COURSE_AUDIENCE,
        )


class TableOfContentsSitemap(AplusSitemap):
    changefreq = 'monthly'
    base_priority = 0.2

    def items(self):
        return CourseInstance.objects.filter(
            view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            visible_to_students=True,
        )

    def location(self, item):
        return reverse('toc', kwargs=item.get_url_kwargs())


all_sitemaps = {
    'exercise_exercise': BaseExerciseSitemap,
    'exercise_chapter': CourseChapterSitemap,
    'exercise_toc': TableOfContentsSitemap,
}
