from django.shortcuts import redirect, get_object_or_404
from course.models import Course, CourseInstance
from exercise.exercise_models import BaseExercise

def course(request, course_url=None):
    course = get_object_or_404(Course, url=course_url)
    return redirect(course.instances.first().get_absolute_url(), permanent=True)

def instance(request, course_url=None, instance_url=None):
    instance = get_object_or_404(CourseInstance, url=instance_url, course__url=course_url)
    return redirect(instance.get_absolute_url(), permanent=True)

def exercise(request, exercise_id=None):
    exercise = get_object_or_404(BaseExercise, id=exercise_id)
    return redirect(exercise.get_absolute_url(), permanent=True)

def instance_exercise(request, course_url=None, instance_url=None, exercise_id=None):
    instance = get_object_or_404(CourseInstance, url=instance_url, course__url=course_url)
    exercise = get_object_or_404(BaseExercise, id=exercise_id, course_module__course_instance=instance)
    return redirect(exercise.get_absolute_url(), permanent=True)
