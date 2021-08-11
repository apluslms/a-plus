from typing import Optional, Protocol

from course.models import CourseInstance, CourseModule
from lib.helpers import empty_at_runtime


@empty_at_runtime
class SupportsGetCourseInstanceObject(Protocol):
    def get_course_instance_object(self) -> Optional[CourseInstance]: ...


@empty_at_runtime
class SupportsGetCourseModuleObject(Protocol):
    def get_course_module_object(self) -> Optional[CourseModule]: ...
