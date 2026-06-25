from django.urls import resolve, Resolver404
from django.shortcuts import render
from course.models import Course, CourseInstance

def _get_course_instance_from_url(request):
    try:
        url_match = resolve(request.path_info)
        course_slug = url_match.kwargs.get('course_slug')
        instance_slug = url_match.kwargs.get('instance_slug')
    except Resolver404:
        course_slug = None
        instance_slug = None

    course = Course.objects.filter(url=course_slug).first() if course_slug else None
    instance = (
        CourseInstance.objects.filter(course=course, url=instance_slug).first()
        if course and instance_slug else None
    )

    return course, instance

def _get_context(request):
    course, instance = _get_course_instance_from_url(request)
    base_template = 'course/course_base.html' if instance else 'base.html'

    context = {
        'show_language_toggle': True,
        'course': course,
        'instance': instance,
        'base_template': base_template
    }

    return context

# pylint: disable-next=unused-argument
def error_404(request, exception=None):
    context = _get_context(request)
    return render(request, '404.html', context, status=404)

# pylint: disable-next=unused-argument
def error_403(request, exception=None):
    context = _get_context(request)
    return render(request, '403.html', context, status=403)

# pylint: disable-next=unused-argument
def error_500(request, exception=None):
    context = {
        'show_language_toggle': True,  
    }
    return render(request, '500.html', context, status=500)
