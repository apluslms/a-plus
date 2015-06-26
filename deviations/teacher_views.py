from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import render_to_response, redirect

from course.context import CourseContext
from course.decorators import access_teacher_resource
from deviations.forms import DeadlineRuleDeviationForm
from deviations.models import DeadlineRuleDeviation
from exercise.exercise_models import BaseExercise
from userprofile.models import UserProfile


@access_teacher_resource
def list_dl_deviations(request,
                                  course_url=None, instance_url=None,
                                  course=None, course_instance=None):
    """
    Lists deadline rule deviations for a course instance.
    """
    deviations = DeadlineRuleDeviation.objects.filter(
        exercise__course_module__course_instance=course_instance
    )
    return render_to_response("deviations/teacher/list_dl.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        deviations=deviations
    ))


@access_teacher_resource
def add_dl_deviations(request,
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

        return redirect(list_dl_deviations,
            course_url=course.url,
            instance_url=course_instance.url
        )

    form = DeadlineRuleDeviationForm(instance=course_instance)

    return render_to_response("deviations/teacher/add_dl.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        form=form
    ))


@access_teacher_resource
def remove_dl_deviation(request,
                                   course_url=None, instance_url=None,
                                   deviation_id=None,
                                   course=None, course_instance=None):
    """
    Removes a deadline rule deviation.
    """
    if request.method == "POST":
        try:
            deviation = DeadlineRuleDeviation.objects.get(
                id=deviation_id,
                exercise__course_module__course_instance=course_instance)
            deviation.delete()
        except DeadlineRuleDeviation.DoesNotExist:
            messages.warning(request,
                _("Dead line deviation ({id:d}) does not exist.") \
                    .format(id=deviation_id))
    return redirect(list_dl_deviations,
        course_url=course.url,
        instance_url=course_instance.url
    )
