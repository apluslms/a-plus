import json
import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import HttpResponseForbidden
from django.http.response import JsonResponse
from django.shortcuts import render_to_response, redirect
from django.template import loader
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from course.context import CourseContext
from course.decorators import access_teacher_resource, \
    access_assistant_resource, access_graded_resource
from exercise.models import BaseExercise
from exercise.presentation.results import ResultTable
from exercise.submission_forms import SubmissionReviewForm, \
    SubmissionCreateAndReviewForm, BathSubmissionCreateAndReviewForm
from exercise.submission_models import Submission
from lib.helpers import extract_form_errors
from notification.models import Notification
from userprofile.models import UserProfile


logger = logging.getLogger('aplus.exercise')


@access_assistant_resource
def results_table(request, course_url=None, instance_url=None,
                  course=None, course_instance=None):
    """
    Renders a results page for a course instance. The results contain individual
    scores for each student on each exercise.
    """
    table = ResultTable(course_instance)
    table_html = loader.render_to_string("exercise/staff/_results_table.html", {
        "result_table": table
    })
    return render_to_response("exercise/staff/results.html", CourseContext(
        request,
        course_instance=course_instance,
        result_table=table,
        table_html=table_html
    ))


@access_assistant_resource
def list_exercise_submissions(request, course_url=None, instance_url=None,
                              exercise_id=None,
                              course=None, course_instance=None,
                              exercise=None):
    """
    Lists all submissions for a given exercise.

    """
    template = "_submissions_table.html" if request.is_ajax() \
        else "list_submissions.html"
    return render_to_response("exercise/staff/" + template, CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        exercise=exercise,
        submissions=exercise.submissions.all(),
    ))


@access_assistant_resource
def inspect_exercise_submission(request, course_url=None, instance_url=None,
                                exercise_id=None, submission_id=None,
                                course=None, course_instance=None,
                                exercise=None, submission=None):
    """
    Inspects a submission.
    """
    return render_to_response("exercise/staff/inspect_submission.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        exercise=exercise,
        submission=submission,
    ))


@access_assistant_resource
def resubmit_to_service(request, course_url=None, instance_url=None,
                        exercise_id=None, submission_id=None,
                        course=None, course_instance=None,
                        exercise=None, submission=None):
    """
    Re-submits a submission to the assessment service. This is meant to be used
    in situations where the assessment service behaved incorrectly. Will use
    the late submission reductions.

    This view overwrites the grading_data, service_points, service_max_points,
    grade and grading_time of the Submission instance and there is no way to
    see the old data.
    """
    if not request.method == "POST":
        return HttpResponseForbidden(_("Only HTTP POST allowed."))

    # Sets feedback using Django messages.
    _ = exercise.grade(request, submission)

    return redirect(inspect_exercise_submission,
        course_url=course.url,
        instance_url=course_instance.url,
        exercise_id=exercise.id,
        submission_id=submission.id)


@access_graded_resource
def assess_submission(request, course_url=None, instance_url=None,
                      exercise_id=None, submission_id=None,
                      course=None, course_instance=None,
                      exercise=None, submission=None):
    """
    Allows manual assessing of a submission. Changing the grade or writing
    feedback will send a notification to the submitters. Late submission
    penalty is not applied to the grade.
    """
    grader = UserProfile.get_by_request(request)

    if request.method == "POST":
        form = SubmissionReviewForm(request.POST, exercise=exercise)
        if form.is_valid():
            submission.set_points(form.cleaned_data["points"], exercise.max_points,
                                  no_penalties=True)
            submission.grader = grader
            submission.assistant_feedback = form.cleaned_data["assistant_feedback"]
            submission.feedback = form.cleaned_data["feedback"]
            submission.set_ready()
            submission.save()

            sub = _('New assistant feedback')
            msg = _('<p>You have new personal feedback to exercise '
                    '<a href="{url}">{name}</a>:</p>{message}').format(
                url=submission.get_absolute_url(),
                name=exercise.name,
                message=submission.feedback,
            )
            for student in submission.submitters.all():
                Notification.send(grader, student, course_instance, sub, msg)

            messages.success(request, _(
                "The review was saved successfully and the submitters were notified."
            ))
            return redirect(inspect_exercise_submission,
                course_url=course.url,
                instance_url=course_instance.url,
                exercise_id=exercise.id,
                submission_id=submission.id)
    else:
        form = SubmissionReviewForm(
            exercise=exercise,
            initial={
                "points": submission.grade,
                "feedback": submission.feedback,
                "assistant_feedback": submission.assistant_feedback
            }
        )
    return render_to_response("exercise/staff/assess_submission.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        exercise=exercise,
        submission=submission,
        form=form
    ))


@access_graded_resource
def create_and_assess_submission(request, course_url=None, instance_url=None,
                                 exercise_id=None,
                                 course=None, course_instance=None,
                                 exercise=None):
    """
    Creates a new assessed submission for a selected student.

    Note: Does not notify the students.
    """
    if not request.method == "POST":
        return HttpResponseForbidden(_("Only HTTP POST allowed."))

    # Use form to parse and validate the request.
    form = SubmissionCreateAndReviewForm(
        request.POST,
        exercise=exercise,
        students_choices=course_instance.get_student_profiles()
    )
    if not form.is_valid():
        messages.error(request, _("Invalid POST data: <pre>{error}</pre>").format(
            error="\n".join(extract_form_errors(form))
        ))
        return redirect(list_exercise_submissions,
            course_url=course.url,
            instance_url=course_instance.url,
            exercise_id=exercise.id)

    new_submission = Submission.objects.create(exercise=exercise)
    new_submission.submitters = form.cleaned_data.get("students") \
        or form.cleaned_data.get("students_by_student_id")
    new_submission.feedback = form.cleaned_data.get("feedback")
    new_submission.set_points(
        form.cleaned_data.get("points"),
        exercise.max_points,
        no_penalties=True)
    new_submission.submission_time = form.cleaned_data.get("submission_time")
    new_submission.grading_time = timezone.now()
    new_submission.set_ready()
    new_submission.save()

    messages.success(request, _("New submission stored."))
    return redirect(inspect_exercise_submission,
        course_url=course.url,
        instance_url=course_instance.url,
        exercise_id=exercise.id,
        submission_id=new_submission.id)


@access_teacher_resource
def batch_create_and_assess_submissions(request, course_url=None, instance_url=None,
                                        course=None, course_instance=None):
    """
    Creates new assessed submissions from posted JSON data.

    Note: Does not notify the students.
    """
    if not request.method == "POST":
        return HttpResponseForbidden(_("Only HTTP POST allowed."))

    error = False
    try:
        submissions_json = json.loads(request.POST.get("submissions_json", ""))
    except Exception as e:
        logger.exception("Failed to parse submission batch JSON from user: %s",
                         request.user.username)
        messages.error(request, _("Failed to parse the JSON: {error}").format(
            error=str(e)
        ))
        error = True

    if not error and not "objects" in submissions_json:
        messages.error(request, _('Missing JSON field: objects'))
        error = True

    validated_forms = []
    if not error:
        count = 0
        for submission_json in submissions_json["objects"]:
            count += 1
            if not "exercise_id" in submission_json:
                messages.error(request,
                    _('Missing field "exercise_id" in object {count:d}.').format(
                        count=count
                    ))
                error = True
                continue

            exercise = BaseExercise.objects \
                .filter(id=submission_json["exercise_id"]) \
                .first()
            if not exercise:
                messages.error(request,
                    _('Unknown exercise_id {id:d} in object {count:d}.').format(
                        count=count,
                        id=submission_json["exercise_id"],
                    ))
                error = True
                continue

            # Use form to parse and validate individual objects.
            form = BathSubmissionCreateAndReviewForm(
                submission_json, exercise=exercise)
            if form.is_valid():
                validated_forms.append(form)
            else:
                messages.error(request,
                    _("Invalid fields in object {count:d}: <pre>{error}</pre>").format(
                        count=count,
                        error="\n".join(extract_form_errors(form))
                    ))
                error = True

    if not error:
        teacher = UserProfile.get_by_request(request)
        for form in validated_forms:
            new_submission = Submission.objects.create(exercise=form.exercise)
            new_submission.submitters = form.cleaned_data.get("students") \
                or form.cleaned_data.get("students_by_student_id")
            new_submission.feedback = form.cleaned_data.get("feedback")
            new_submission.set_points(
                form.cleaned_data.get("points"),
                new_submission.exercise.max_points,
                no_penalties=True)
            new_submission.submission_time = form.cleaned_data.get("submission_time")
            new_submission.grading_time = timezone.now()
            new_submission.grader = form.cleaned_data.get("grader") or teacher
            new_submission.set_ready()
            new_submission.save()
        messages.success(request, _("New submissions stored."))

    return redirect('course-edit',
        course_url=course.url,
        instance_url=course_instance.url)


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
        page = exercise.load(request, [])
        if page.is_loaded:
            metadata["name"] = page.meta["title"]
            metadata["description"] = page.meta["description"]
            metadata["success"] = True
        else:
            metadata["message"] = "Failed to load the resource."
    except ValidationError as e:
        metadata["message"] = " ".join(e.messages)

    return JsonResponse(metadata)
