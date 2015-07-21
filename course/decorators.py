from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.six import wraps
from django.utils.translation import ugettext_lazy as _

from course.models import Course, CourseInstance, CourseModule, CourseChapter
from exercise.models import LearningObject, Submission


COURSE_KEY = "course_url"
INSTANCE_KEY = "instance_url"
MODULE_KEY = "module_url"
MODULE_ID_KEY = "module_id"
CHAPTER_KEY = "chapter_url"
EXERCISE_KEY = "exercise_id"
SUBMISSION_KEY = "submission_id"


def _resource(view_func):
    """
    Adds the resource objects to keyword arguments based on the URL pattern.
    No authorization at this stage!
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if COURSE_KEY in kwargs:
            course = get_object_or_404(Course,
                url=kwargs[COURSE_KEY])
            kwargs["course"] = course
            if INSTANCE_KEY in kwargs:
                instance = get_object_or_404(CourseInstance,
                    course=course,
                    url=kwargs[INSTANCE_KEY])
                kwargs["course_instance"] = instance
                if MODULE_KEY in kwargs:
                    module = get_object_or_404(CourseModule,
                        url=kwargs[MODULE_KEY],
                        course_instance=instance)
                    kwargs["module"] = module
                    if CHAPTER_KEY in kwargs:
                        kwargs["chapter"] = get_object_or_404(CourseChapter,
                            url=kwargs[CHAPTER_KEY],
                            course_module=module)
                elif MODULE_ID_KEY in kwargs:
                    kwargs["module"] = get_object_or_404(CourseModule,
                        id=kwargs[MODULE_ID_KEY],
                        course_instance=instance)
                if EXERCISE_KEY in kwargs:
                    exercise = get_object_or_404(LearningObject,
                        id=kwargs[EXERCISE_KEY],
                        course_module__course_instance=instance)\
                        .as_leaf_class()
                    kwargs["exercise"] = exercise
                    if SUBMISSION_KEY in kwargs:
                        kwargs["submission"] = get_object_or_404(Submission,
                            id=kwargs[SUBMISSION_KEY],
                            exercise__id=exercise.id)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def access_resource(view_func):
    """
    Accesses the resource selected by named URL patterns and checks the
    required normal access right. Adds the accessed model objects as
    new keyword arguments for the view function.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        instance = kwargs.get("course_instance", None)
        if instance:
            if not instance.is_visible_to(request.user):
                raise PermissionDenied()
            if not instance.is_course_staff(request.user):
                chapter = kwargs.get("chapter", None)
                if chapter and not chapter.course_module.is_after_open():
                    raise PermissionDenied()
                exercise = kwargs.get("exercise", None)
                if exercise and not exercise.course_module.is_after_open():
                    raise PermissionDenied()
                submission = kwargs.get("submission", None)
                if submission and not submission.is_submitter(request.user):
                    raise PermissionDenied()
        return view_func(request, *args, **kwargs)

    return _resource(login_required(_wrapped_view))


def access_teacher_resource(view_func):
    """
    Accesses the resource like the first function but requires teacher rights.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        course = kwargs.get("course", None)
        if not (course and course.is_teacher(request.user)):
            raise PermissionDenied()
        # Other model objects belong to the same course.
        return view_func(request, *args, **kwargs)

    return _resource(login_required(_wrapped_view))


def access_assistant_resource(view_func):
    """
    Accesses the resource like the first function but requires assistant rights.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        instance = kwargs.get("course_instance", None)
        if not (instance and instance.is_course_staff(request.user)):
            raise PermissionDenied()
        # Other model objects belong to the same course instance.
        return view_func(request, *args, **kwargs)

    return _resource(login_required(_wrapped_view))


def access_graded_resource(view_func):
    """
    Accesses the resource like the first function but requires grading rights.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        instance = kwargs.get("course_instance", None)
        if not (instance and instance.is_course_staff(request.user)):
            raise PermissionDenied()
        exercise = kwargs.get("exercise", None)
        if not (exercise and (exercise.allow_assistant_grading \
                or instance.is_teacher(request.user))):
            raise PermissionDenied(
                _("Assistant grading is not allowed for this exercise."))
        return view_func(request, *args, **kwargs)

    return _resource(login_required(_wrapped_view))
