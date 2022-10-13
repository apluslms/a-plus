from django.http import Http404

from authorization.api.mixins import ApiResourceMixin
from authorization.permissions import ACCESS
from ..models import (
    CourseInstance,
    CourseModule,
)
from ..viewbase import (
    CourseInstanceBaseMixin,
    CourseModuleBaseMixin,
)


class CourseResourceMixin(CourseInstanceBaseMixin, ApiResourceMixin):
    course_kw = 'course_id'
    access_mode = ACCESS.ANONYMOUS # not really used, see get_access_mode() below

    def get_course_instance_object(self):
        course_id = self.kwargs.get(self.course_kw, None)
        if course_id is None:
            return None
        try:
            return CourseInstance.objects.get(id=course_id)
        except CourseInstance.DoesNotExist as exc:
            raise Http404("Course not found") from exc

    def get_access_mode(self):
        # This method is defined here because some permissions expect view classes
        # to have this method. Access mode was not really intended to be used by
        # the API, though. Class CourseInstanceBaseMixin actually defines this
        # method, but it calls super(), which would crash unless this class
        # defined this method.
        return self.access_mode


class CourseModuleResourceMixin(CourseModuleBaseMixin, ApiResourceMixin):
    module_kw = 'exercisemodule_id'

    def get_course_module_object(self):
        module_id = self.kwargs.get(self.module_kw, None)
        if module_id is None:
            return None
        try:
            return CourseModule.objects.get(id=module_id, course_instance=self.instance)
        except CourseModule.DoesNotExist:
            return None
