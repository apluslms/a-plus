from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.http.response import Http404, JsonResponse
from django.shortcuts import render_to_response, redirect
from django.utils.translation import ugettext_lazy as _

from course.context import CourseContext
from course.decorators import access_teacher_resource
from course.forms import CourseModuleForm, BaseExerciseForm, \
    ExerciseWithAttachmentForm, DeadlineRuleDeviationForm
from exercise.models import BaseExercise, ExerciseWithAttachment, \
    CourseModule, DeadlineRuleDeviation 
from userprofile.models import UserProfile


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
                       course_url=None, instance_url=None, module_url=None,
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
                                module_url=module.url)
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
                  course_url=None, instance_url=None, module_url=None,
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
                         course_url=None, instance_url=None, module_url=None,
                         exercise_id=None, exercise_type=None,
                         course=None, course_instance=None, module=None,
                         exercise=None):
    """
    Edits and creates exercises.
    """
    add = exercise is None
    if add:
        if exercise_type == "exercise_with_attachment":
            exercise = ExerciseWithAttachment(course_module=module)
        elif exercise_type is None:
            exercise = BaseExercise(course_module=module)
        else:
            return Http404(_("Unknown exercise type given."))

    if request.method == "POST":
        if isinstance(exercise, ExerciseWithAttachment):
            form = ExerciseWithAttachmentForm(request.POST,
                                              request.FILES,
                                              instance=exercise)
        else:
            form = BaseExerciseForm(request.POST, instance=exercise)
        
        if form.is_valid():
            exercise = form.save()
            messages.success(request,
                             _('The exercise was saved successfully.'))
            if add:
                return redirect(add_or_edit_exercise,
                                course_url=course.url,
                                instance_url=course_instance.url,
                                exercise_id=exercise.id)
    else:
        if isinstance(exercise, ExerciseWithAttachment):
            form = ExerciseWithAttachmentForm(instance=exercise)
        else:
            form = BaseExerciseForm(instance=exercise)

    return render_to_response("course/teacher/edit_exercise.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        exercise=exercise,
        form=form
    ))


@access_teacher_resource
def remove_exercise(request,
                    course_url=None, instance_url=None, module_url=None,
                    exercise_id=None,
                    course=None, course_instance=None, module=None,
                    exercise=None):
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


@access_teacher_resource
def fetch_exercise_metadata(request,
                            course_url=None, instance_url=None,
                            course=None, course_instance=None):
    """
    Fetches meta data from an exercise URL.
    """
    exercise_url = request.GET.get("exercise_url", None)
    metadata = {"success": False}

    validate = URLValidator()
    try:
        validate(exercise_url)

        exercise = BaseExercise(service_url=exercise_url)
        exercise_page = exercise.get_page("")
        metadata["name"] = exercise_page.meta["title"]
        metadata["description"] = exercise_page.meta["description"]
        metadata["success"] = True
        
    except ValidationError as e:
        metadata["message"] = " ".join(e.messages)
    except Exception as e:
        metadata["message"] = "No meta data found."

    return JsonResponse(metadata)


@access_teacher_resource
def list_deadline_rule_deviations(request,
                                  course_url=None, instance_url=None,
                                  course=None, course_instance=None):
    """
    Lists deadline rule deviations for a course instance.
    """
    deviations = DeadlineRuleDeviation.objects.filter(
        exercise__course_module__course_instance=course_instance
    )
    return render_to_response("course/teacher/list_deadline_rule_deviations.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        deviations=deviations
    ))


@access_teacher_resource
def add_deadline_rule_deviations(request,
                                 course_url=None, instance_url=None,
                                 course=None, course_instance=None):
    """
    Adds a group of deadline rule deviations for a course instance.
    """
    if request.method == "POST":
        minutes = request.POST["minutes"]
        for user_id in request.POST.getlist("submitter"):
            try:
                submitter = UserProfile.objects.get(id=user_id)
                for exercise_id in request.POST.getlist("exercise"):
                    try:
                        exercise = BaseExercise.objects.get(id=exercise_id,
                            course_module__course_instance=course_instance)
                    
                        dl_rule_deviation = DeadlineRuleDeviation.objects.create(
                            exercise=exercise,
                            submitter=submitter,
                            extra_minutes=minutes
                        )
                        dl_rule_deviation.save()
    
                    except BaseExercise.DoesNotExist:
                        messages.warning(request,
                            _("Selected exercise ({id:d}) does not exist in the course instance.") \
                                .format(id=exercise_id))

                    except IntegrityError:
                        messages.warning(request,
                            _("Dead line deviation already exists for {user} in {exercise}! "
                              "Remove it before trying to add a new one.") \
                                .format(user=str(submitter), exercise=str(exercise)))
            
            except UserProfile.DoesNotExist:
                messages.warning(request,
                    _("Selected user ({id:d}) does not exist.") \
                        .format(id=user_id))

        return redirect(list_deadline_rule_deviations,
            course_url=course.url,
            instance_url=course_instance.url
        )

    form = DeadlineRuleDeviationForm(instance=course_instance)

    return render_to_response("course/teacher/add_deadline_rule_deviations.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        form=form
    ))


@access_teacher_resource
def remove_deadline_rule_deviation(request,
                                   course_url=None, instance_url=None,
                                   dlrd_id=None,
                                   course=None, course_instance=None):
    """
    Removes a deadline rule deviation.
    """
    if request.method == "POST":
        try:
            deviation = DeadlineRuleDeviation.objects.get(
                id=dlrd_id,
                exercise__course_module__course_instance=course_instance)
            deviation.delete()
        except DeadlineRuleDeviation.DoesNotExist:
            messages.warning(request,
                _("Dead line deviation ({id:d}) does not exist.") \
                    .format(id=dlrd_id))
    return redirect(list_deadline_rule_deviations,
        course_url=course.url,
        instance_url=course_instance.url
    )
