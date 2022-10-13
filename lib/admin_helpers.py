import datetime
from typing import Optional, Sequence, Tuple

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from course.models import CourseInstance


class RecentCourseInstanceListFilter(admin.SimpleListFilter):
    """List filter for CourseInstances in the Django admin site.

    This filter picks only the 15 latest course instances so that
    the filter sidebar is not filled with hundreds of course instances.

    Child classes may override the class variable course_instance_query.
    It specifies how to query CourseInstances from the model, e.g.,
    from Submission, it is 'exercise__course_module__course_instance'.
    """
    title = _('MODEL_NAME_COURSE_INSTANCE')
    parameter_name = 'course_instance'
    course_instance_query = 'course_instance'
    recent_weeks = 12

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> Sequence[Tuple[str, str]]:
        now = timezone.now()
        course_instances = CourseInstance.objects.filter(
            starting_time__lte=now,
            ending_time__gte=now - datetime.timedelta(weeks=self.recent_weeks),
        ).order_by('-starting_time')[:15]
        for course_instance in course_instances:
            yield (str(course_instance.pk), str(course_instance))
    # pylint: disable=inconsistent-return-statements
    def queryset(self, request: HttpRequest, queryset: QuerySet) -> Optional[QuerySet]:
        course_instance_id = self.value()
        if course_instance_id is not None:
            return queryset.filter(**{self.course_instance_query: course_instance_id})
