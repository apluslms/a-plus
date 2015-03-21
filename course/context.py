from django.template.context import Context, RequestContext
from django.template.context import get_standard_processors

class CourseContext(RequestContext):
    """
    This subclass of template.Context automatically populates itself using
    the processors defined in TEMPLATE_CONTEXT_PROCESSORS.
    """
    def __init__(self, request, course=None, course_instance=None, **dict):
        RequestContext.__init__(self,
                                request,
                                dict)
        
        # Initially the user is neither an assistant nor a teacher
        is_assistant    = False
        is_teacher      = False
        
        # If the course is not given, but an instance is, get the instance's course
        if course == None and course_instance != None:
            course = course_instance.course
        
        if request.user.is_authenticated():
            # If the user is authenticated, populate is_assistant and is_teacher fields
            profile     = request.user.userprofile
            
            if course != None and course.is_teacher(profile):
                # Teachers are also allowed to act as assistants
                is_teacher      = True
                is_assistant    = True
            elif course_instance != None and course_instance.is_assistant(profile):
                is_assistant    = True
        
        course_info     = {"is_teacher":    is_teacher,
                           "is_assistant":  is_assistant,
                           "instance":      course_instance,
                           "course":        course,
                           }
        
        self.update(course_info)

        # TODO:
        # For some reason, request is not available in this context even though
        # it should be. Thus temporarily adding it manually.
        self.update({"request": request})

