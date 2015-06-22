from django.template.context import RequestContext
from userprofile.models import UserProfile


class CourseContext(RequestContext):
    """
    Template context that includes values for selected course.
    """
    def __init__(self, request, course=None, course_instance=None, **kwarg):
        RequestContext.__init__(self, request, kwarg)

        if course is None and course_instance is not None:
            course = course_instance.course

        self.update({
            "course": course,
            "instance": course_instance,
            "profile": UserProfile.get_by_request(request),
            "is_teacher": course and course.is_teacher(request.user),
            "is_assistant": course_instance and course_instance.is_assistant(request.user),
            # For some reason, request is not available in this context even though
            # it should be. Thus temporarily adding it manually.
            "request": request
        })
