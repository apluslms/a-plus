from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.six import wraps
from django.utils.translation import ugettext_lazy as _

from course.models import Course, CourseInstance, CourseModule
from exercise.models import LearningObject, Submission


COURSE_KEY = "course_url"
INSTANCE_KEY = "instance_url"
MODULE_KEY = "module_url"
EXERCISE_KEY = "exercise_id"
SUBMISSION_KEY = "submission_id"


class Resources(object):
    """
    Selects the resource objects based on a URL pattern.
    """
    def __init__(self, request, kwargs):
        
        self._kwargs = kwargs
        self.course = None
        self.instance = None
        self.module = None
        self.exercise = None
        self.submission = None

        if COURSE_KEY in kwargs:
            self.course = get_object_or_404(Course,
                url=kwargs[COURSE_KEY])
            if INSTANCE_KEY in kwargs:
                self.instance = get_object_or_404(CourseInstance,
                    course=self.course,
                    url=kwargs[INSTANCE_KEY])
                if MODULE_KEY in kwargs:
                    self.module = get_object_or_404(CourseModule,
                        url=kwargs[MODULE_KEY],
                        course_instance=self.instance)
                if EXERCISE_KEY in kwargs:
                    self.exercise = get_object_or_404(LearningObject,
                        id=kwargs[EXERCISE_KEY],
                        course_module__course_instance=self.instance) \
                        .as_leaf_class()
                    if SUBMISSION_KEY in kwargs:
                        self.submission = get_object_or_404(Submission,
                            id=kwargs[SUBMISSION_KEY],
                            exercise__id=self.exercise.id)

    def kwargs(self):
        if not self.course is None:
            self._kwargs["course"] = self.course
        if not self.instance is None:
            self._kwargs["course_instance"] = self.instance
        if not self.module is None:
            self._kwargs["module"] = self.module
        if not self.exercise is None:
            self._kwargs["exercise"] = self.exercise
        if not self.submission is None:
            self._kwargs["submission"] = self.submission
        return self._kwargs


def access_resource(view_func):
    """
    Accesses the resource selected by named URL patterns and checks the
    required normal access right. Adds the accessed model objects as
    new keyword arguments for the view function.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        res = Resources(request, kwargs)
        if res.instance:
        
            if not res.instance.is_visible_to(request.user):
                raise PermissionDenied()
        
            if not res.instance.is_course_staff(request.user):
            
                if res.exercise \
                and not res.exercise.course_module.is_after_open():
                    raise PermissionDenied()
                
                if res.submission \
                and not res.submission.is_submitter(request.user):
                    raise PermissionDenied()
        
        return view_func(request, *args, **res.kwargs())

    return login_required(_wrapped_view)


def access_teacher_resource(view_func):
    """
    Accesses the resource like the first function but requires teacher rights.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        res = Resources(request, kwargs)
        if res.course \
        and not res.course.is_teacher(request.user):
            raise PermissionDenied()
        # Other model objects belong to the same course.
        return view_func(request, *args, **res.kwargs())

    return login_required(_wrapped_view)


def access_assistant_resource(view_func):
    """
    Accesses the resource like the first function but requires assistant rights.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        res = Resources(request, kwargs)
        if res.instance \
        and not res.instance.is_course_staff(request.user):
            raise PermissionDenied()
        # Other model objects belong to the same course instance.
        return view_func(request, *args, **res.kwargs())

    return login_required(_wrapped_view)


def access_graded_resource(view_func):
    """
    Accesses the resource like the first function but requires grading rights.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        res = Resources(request, kwargs)
        if res.instance \
        and not res.instance.is_course_staff(request.user):
            raise PermissionDenied()
        
        if res.exercise and not res.exercise.allow_assistant_grading \
        and not res.instance.is_teacher(request.user):
            raise PermissionDenied(
                _("Assistant grading is not allowed for this exercise."))

        return view_func(request, *args, **res.kwargs())

    return login_required(_wrapped_view)
