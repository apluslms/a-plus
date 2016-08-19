from authorization.api.mixins import ApiResourceMixin
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

    def get_course_instance_object(self):
        course_id = self.kwargs.get(self.course_kw, None)
        if course_id is None:
            return None
        try:
            return CourseInstance.objects.get(id=course_id)
        except CourseInstance.DoesNotExist:
            return None


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
