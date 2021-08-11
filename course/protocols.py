from typing import Optional, Protocol

from course.models import CourseInstance, CourseModule
from lib.helpers import object_at_runtime


@object_at_runtime
class SupportsGetCourseInstanceObject(Protocol):
    def get_course_instance_object(self) -> Optional[CourseInstance]: ...


@object_at_runtime
class SupportsGetCourseModuleObject(Protocol):
    def get_course_module_object(self) -> Optional[CourseModule]: ...
