from typing import Optional

from course.models import CourseInstance, CourseModule
from lib.helpers import empty_at_runtime


@empty_at_runtime
class SupportsGetCourseInstanceObject:
    def get_course_instance_object(self) -> Optional[CourseInstance]: ...


@empty_at_runtime
class SupportsGetCourseModuleObject:
    def get_course_module_object(self) -> Optional[CourseModule]: ...
