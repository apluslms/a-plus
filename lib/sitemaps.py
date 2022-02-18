import datetime

from django.conf import settings
from django.contrib import sitemaps
from django.utils import timezone

from course.models import CourseInstance, CourseModule
from exercise.models import BaseExercise, CourseChapter


class AplusSitemap(sitemaps.Sitemap):
    # The base priority for pages from old courses.
    # Pages of recent or upcoming courses have the base priority multiplied.
    base_priority = 0.5

    def is_recent_or_upcoming(self, item):
        """
        Return a boolean value indicating if the given item is open now
        or if either the item's start date or end date is within a certain time delta from now.
        """
        if isinstance(item, CourseInstance):
            start_date = item.starting_time
            end_date = item.ending_time
        elif isinstance(item, CourseModule):
            start_date = item.opening_time
            end_date = item.closing_time
        elif isinstance(item, (BaseExercise, CourseChapter)):
            start_date = item.course_module.opening_time
            end_date = item.course_module.closing_time
        else:
            return False
        now = timezone.now()
        delta = datetime.timedelta(settings.SITEMAP_DELTA_DAYS_RECENT_OR_UPCOMING)
        is_recent_or_upcoming = (
            item.is_open(now)
            or now - delta <= start_date <= now + delta
            or now - delta <= end_date <= now + delta
        )
        return is_recent_or_upcoming

    def location(self, item):
        return item.get_display_url()

    def priority(self, item):
        return min(1.0, 2 * self.base_priority) if self.is_recent_or_upcoming(item) else self.base_priority
