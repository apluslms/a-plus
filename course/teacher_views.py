from django.contrib import messages
from django.http.response import Http404
from django.shortcuts import render_to_response, redirect
from django.utils.translation import ugettext_lazy as _

from course.context import CourseContext
from course.decorators import access_teacher_resource
from course.forms import CourseModuleForm
from course.models import CourseModule
from exercise import exercise_forms


@access_teacher_resource
def edit_course(request,
                  course_url=None, instance_url=None,
                  course=None, course_instance=None):
    """
    Presents course components for a teacher to edit.
    """
    context = CourseContext(request,
                            course=course,
                            course_instance=course_instance)
    return render_to_response("course/teacher/course_instance.html", context)


@access_teacher_resource
def add_or_edit_module(request,
                       course_url=None, instance_url=None, module_id=None,
                       course=None, course_instance=None, module=None):
    """
    Edits and creates course modules.
    """
    add = module is None
    if add:
        module = CourseModule(course_instance=course_instance)

    if request.method == "POST":
        form = CourseModuleForm(request.POST, instance=module)
        if form.is_valid():
            module = form.save()
            messages.success(request,
                             _('The course module was saved successfully.'))
            if add:
                return redirect(add_or_edit_module,
                                course_url=course.url,
                                instance_url=course_instance.url,
                                module_id=module.id)
    else:
        form = CourseModuleForm(instance=module)

    return render_to_response("course/teacher/edit_module.html",
                              CourseContext(request,
                                            course=course,
                                            course_instance=course_instance,
                                            module=module,
                                            form=form))


@access_teacher_resource
def remove_module(request,
                  course_url=None, instance_url=None, module_id=None,
                  course=None, course_instance=None, module=None):
    """
    Removes empty course modules.
    """
    exercise_count = module.learning_objects.count()
    if request.method == "POST" and exercise_count == 0:
        module.delete()
        return redirect(edit_course,
                    course_url=course.url,
                    instance_url=course_instance.url)
    return render_to_response("course/teacher/remove_module.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        module=module,
        exercise_count=exercise_count
    ))


@access_teacher_resource
def add_or_edit_exercise(request,
                         course_url=None, instance_url=None, module_id=None,
                         exercise_id=None, exercise_type=None,
                         course=None, course_instance=None, module=None,
                         exercise=None):
    """
    Edits and creates exercises.
    """
    add = exercise is None
    try:
        if request.method == "POST":
            form = exercise_forms.get_form(module, exercise_type, exercise, request)
            if form.is_valid():
                exercise = form.save()
                messages.success(request,
                                 _('The exercise was saved successfully.')
                )
                if add:
                    return redirect(add_or_edit_exercise,
                                    course_url=course.url,
                                    instance_url=course_instance.url,
                                    exercise_id=exercise.id)
        else:
            form = exercise_forms.get_form(module, exercise_type, exercise)
    except TypeError:
        raise Http404()

    return render_to_response("course/teacher/edit_exercise.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        exercise=exercise,
        form=form
    ))


@access_teacher_resource
def remove_exercise(request,
                    course_url=None, instance_url=None, exercise_id=None,
                    course=None, course_instance=None, exercise=None):
    """
    Removes exercises.
    """
    if request.method == "POST":
        exercise.delete()
        return redirect(edit_course,
                        course_url=course.url,
                        instance_url=course_instance.url)
    return render_to_response("course/teacher/remove_exercise.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        exercise=exercise
    ))
