from django.shortcuts import redirect, get_object_or_404
from course.models import Course, CourseInstance
from exercise.exercise_models import BaseExercise

def course(request, course_url=None):
    course = get_object_or_404(Course, url=course_url)
    return redirect('course.views.view_course',
        course_url=course.url,
        permanent=True,
    )

def instance(request, course_url=None, instance_url=None):
    instance = get_object_or_404(CourseInstance, url=instance_url, course__url=course_url)
    return redirect('course.views.view_instance',
        course_url=instance.course.url,
        instance_url=instance.url,
        permanent=True,
    )

def exercise(request, exercise_id=None):
    exercise = get_object_or_404(BaseExercise, id=exercise_id)
    return redirect('exercise',
        course_url=exercise.course_instance.course.url,
        instance_url=exercise.course_instance.url,
        exercise_id=exercise.id,
        permanent=True,
    )
