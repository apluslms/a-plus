# Python
import simplejson as json
from datetime import datetime, timedelta

# Django
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import IntegrityError

# A+
from course.models import CourseInstance
from course.views import teachers_view
from userprofile.models import UserProfile
from exercise.exercise_models import BaseExercise, ExerciseWithAttachment, CourseModule, DeadlineRuleDeviation
from exercise.submission_models import Submission
from exercise.forms import BaseExerciseForm, SubmissionReviewForm, StaffSubmissionForStudentForm, TeacherCreateAndAssessSubmissionForm, \
    ExerciseWithAttachmentForm, DeadlineRuleDeviationForm
from course.context import CourseContext
from django.utils import simplejson
from notification.models import Notification

@login_required
def list_exercise_submissions(request, exercise_id):
    """
    This view lists all submissions for a given exercise. The view can only be accessed
    by course staff, meaning the teachers and assistants of the course.
    
    @param exercise_id: the ID of the exercise which the submissions are for
    """
    exercise        = get_object_or_404(BaseExercise, id=exercise_id)
    has_permission  = exercise.get_course_instance().is_staff(request.user.get_profile()) 
    
    if not has_permission:
        # TODO: Missing translation.
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    submissions     = exercise.submissions.all()
    
    return render_to_response("exercise/exercise_submissions.html", CourseContext(
        request,
        submissions=submissions,
        exercise=exercise,
        course_instance=exercise.course_module.course_instance,
    ))

@login_required
def inspect_exercise_submission(request, submission_id):
    """
    This is the view for course personnel for inspecting and manually assessing
    exercise submissions. To access this view, the user must be either an assistant
    or a teacher on the course where the exercise is held on.
    
    @param submission_id: the ID of the submission to be inspected
    """
    submission      = get_object_or_404(Submission, id=submission_id)
    exercise        = submission.exercise
    has_permission  = exercise.get_course_instance().is_staff(request.user.get_profile())     
    
    if not has_permission:
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    return render_to_response("exercise/inspect_submission.html", CourseContext(
        request,
        submission=submission,
        exercise=exercise,
        course_instance=exercise.get_course_instance()
    ))

@login_required
def add_or_edit_exercise(request, module_id, exercise_id=None, exercise_type=None):
    """ 
    This page can be used by teachers to add new exercises and edit existing ones.
    """
    module          = get_object_or_404(CourseModule, id=module_id)
    course_instance = module.course_instance
    
    has_permission  = course_instance.is_teacher(request.user.get_profile()) or\
        request.user.is_superuser or request.user.is_staff
    
    if not has_permission:
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    if exercise_id != None:
        exercise = get_object_or_404(module.learning_objects, id=exercise_id).as_leaf_class()
    else:
        if exercise_type == "exercise_with_attachment":
            exercise = ExerciseWithAttachment(course_module=module)
        else:
            exercise = BaseExercise(course_module=module)
    
    if request.method == "POST":
        if type(exercise) is BaseExercise:
            form = BaseExerciseForm(request.POST, instance=exercise)
        elif type(exercise) is ExerciseWithAttachment:
            form = ExerciseWithAttachmentForm(request.POST, request.FILES, instance=exercise)

        if form.is_valid():
            exercise = form.save()
            messages.success(request, _('The exercise was saved successfully.'))
    else:
        if type(exercise) is BaseExercise:
            form = BaseExerciseForm(instance=exercise)
        elif type(exercise) is ExerciseWithAttachment:
            form = ExerciseWithAttachmentForm(instance=exercise)
    
    return render_to_response("exercise/edit_exercise.html", CourseContext(
        request,
        course_instance=course_instance,
        exercise=exercise,
        form=form
    ))

@login_required
def remove_exercise(request, module_id, exercise_id):
    """ 
    This page can be used by teachers to remove an existing exercise.
    """
    module          = get_object_or_404(CourseModule, id=module_id)
    course_instance = module.course_instance
    
    has_permission  = course_instance.is_teacher(request.user.get_profile()) or request.user.is_superuser or request.user.is_staff
    
    if not has_permission:
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    exercise = get_object_or_404(module.learning_objects, id=exercise_id).as_leaf_class()    

    if request.method == "POST":
        exercise.delete()
        return redirect(teachers_view, course_instance.course.url, course_instance.url)

    return render_to_response("exercise/remove_exercise.html", CourseContext(
        request,
        course_instance=course_instance,
        exercise=exercise
    ))

@login_required
def assess_submission(request, submission_id):
    """
    This view is used for assessing the given exercise submission. When
    assessing, the teacher or assistant may write verbal feedback and give a
    numeric grade for the submission. Changing the grade or writing feedback
    will send a notification to the submitters.
    Late submission penalty is not applied to the grade.
    
    @param submission_id: the ID of the submission to assess
    """
    submission = get_object_or_404(Submission, id=submission_id)
    exercise = submission.exercise
    grader = request.user.get_profile()
    
    if exercise.allow_assistant_grading:
        # Both the teachers and assistants are allowed to assess
        has_permission = exercise.get_course_instance().is_staff(grader)
    else:
        # Only teacher is allowed to assess
        has_permission = exercise.get_course_instance().is_teacher(request.user.get_profile())
    
    if not has_permission:
        return HttpResponseForbidden(_("You are not allowed to access this view."))

    
    form = SubmissionReviewForm(
        exercise=exercise,
        initial={
            "points": submission.grade,
            "feedback": submission.feedback,
            "assistant_feedback": submission.assistant_feedback
        }
    )
    if request.method == "POST":
        form = SubmissionReviewForm(request.POST, exercise=exercise)
        if form.is_valid():
            submission.set_points(form.cleaned_data["points"], exercise.max_points, no_penalties=True)
            submission.grader = grader
            submission.assistant_feedback = form.cleaned_data["assistant_feedback"]
            submission.feedback = form.cleaned_data["feedback"]
            submission.set_ready()
            submission.save()
            breadcrumb = exercise.get_breadcrumb()
            for student in submission.submitters.all():
                Notification.send(
                    grader,
                    student,
                    exercise.get_course_instance(),
                    'New assistant feedback',
                    '<p>You have new assistant feedback to exercise <a href="' + breadcrumb[2][1]+'">' + exercise.name +'</a>:</p>'\
                        + submission.assistant_feedback
                )
            messages.success(request, _("The review was saved successfully."))
            return redirect(inspect_exercise_submission, submission_id=submission.id)
    
    return render_to_response("exercise/submission_assessment.html", CourseContext(
        request,
        course_instance=exercise.get_course_instance(),
        exercise=exercise,
        submission=submission,
        form=form)
    )


@login_required
def fetch_exercise_metadata(request):
    exercise_url    = request.GET.get("exercise_url", None)
    metadata = {"success": False}
    
    validate        = URLValidator(verify_exists=True)
    
    try:
        validate(exercise_url)
        
        exercise            = BaseExercise(service_url=exercise_url)
        exercise_page       = exercise.get_page("")
        metadata["name"]    = exercise_page.meta["title"]
        metadata["description"] = exercise_page.meta["description"]
        metadata["success"] = True
    except ValidationError as e:
        metadata["message"] = " ".join(e.messages)
    except Exception as e:
        metadata["message"] = "No metadata found."
    
    return HttpResponse(simplejson.dumps(metadata), content_type="application/json")


@login_required
def resubmit_to_service(request, submission_id):
    """
    This view implements the staff-only re-submission feature. It is meant to be
    used in situations where the assessment service behaved incorrectly so that
    the grading_data is incorrect or the state of the submission never became
    ready.

    This view overwrites the grading_data, service_points, service_max_points,
    grade and grading_time of the Submission instance and there is no way to see
    the old data.

    @param request: HttpRequest from Django
    @param submission_id: id of the Submission instance that needs to be
    re-submitted
    @return: HttpResponseRedirect redirecting to the staff's submission
    inspection page
    """
    submission = Submission.objects.get(id=submission_id)

    has_permission = submission.exercise.get_course_instance().is_staff(
        request.user.get_profile())

    if not has_permission:
        return HttpResponseForbidden(
            _("You are not allowed to access this view."))

    try:
        # Try submitting the submission to the exercise service. The submission
        # is done with a multipart POST request that contains all the files and
        # POST parameters that were originally submitted.
        response_page = submission.submit_to_service()
    except Exception, e:
        messages.error(request,
            _('Connecting to the assessment server failed! (%s)') % str(e))

    if response_page and response_page.is_accepted:
        submission.feedback = response_page.content
        submission.set_waiting()

        if response_page.is_graded:
            if (response_page.max_points != None and not (response_page.exercise.max_points != 0 and response_page.max_points == 0)
                    and response_page.points <= response_page.max_points):
                submission.set_points(response_page.points, response_page.max_points)
                submission.set_ready()

                # Add a success message and redirect the staff user to view the
                # submission
                messages.success(request, _('The exercise was re-submitted and re-graded successfully. Submission points: %d/%d.')
                    % (submission.grade, submission.exercise.max_points)
                )
            else:
                submission.set_error()
                messages.error(request, _("The response from the assessment service was erroneous."))
        else:
            messages.success(request, _('The exercise was re-submitted successfully and is now waiting to be graded.'))

        submission.save()

    else:
        messages.warning(request, _('The exercise could not be re-graded. Please check the page below for errors.'))

    return redirect(submission.get_staff_url())


@login_required
def create_and_assess_submission(request, exercise_id):
    exercise = get_object_or_404(BaseExercise, id=exercise_id)
    grader = request.user.get_profile()

    if exercise.allow_assistant_grading:
        # Both the teachers and assistants are allowed to submit for students
        has_permission = exercise.get_course_instance().is_staff(grader)
    else:
        # Only teachers are allowed to submit for students
        has_permission = exercise.get_course_instance().is_teacher(request.user.get_profile())

    if not has_permission:
        return HttpResponseForbidden(_("You are not allowed to access this view."))

    if not request.method == "POST":
        return HttpResponseForbidden(_("Only HTTP POST allowed."))

    student_choices = UserProfile.objects.filter(
        submissions__in=Submission.objects.filter(exercise__course_module__course_instance=exercise.course_instance)
    )
    form = StaffSubmissionForStudentForm(
        request.POST,
        exercise=exercise,
        students_choices=student_choices)

    if form.is_valid():
        new_submission = Submission.objects.create(exercise=exercise)
        new_submission.submitters = form.cleaned_data.get("students")
        new_submission.feedback = form.cleaned_data.get("feedback")
        new_submission.set_points(form.cleaned_data.get("points"), exercise.max_points, no_penalties=True)
        new_submission.submission_time = form.cleaned_data.get("submission_time")
        new_submission.grading_time = datetime.now()
        new_submission.set_ready()
        new_submission.save()

        return HttpResponse("New submission created successfully.")
    else:
        return HttpResponseBadRequest("Invalid POST data.")


@login_required
def create_and_assess_submission_batch(request, course_instance_id):
    course_instance = get_object_or_404(CourseInstance, id=course_instance_id)
    teacher = request.user.get_profile()

    has_permission = course_instance.is_teacher(teacher)
    if not has_permission:
        return HttpResponseForbidden(_("You are not allowed to access this view."))

    if not request.method == "POST":
        return HttpResponseForbidden(_("Only HTTP POST allowed."))

    # Parse the JSON string.
    try:
        submissions_json = json.loads(request.POST.get("submissions_json"))["objects"]
    except:
        # TODO: Pokemon error handling
        return HttpResponseBadRequest(_("Invalid JSON"))

    validated_forms = []
    # Validate all the data before saving anything.
    for submission_json in submissions_json:
        exercise = get_object_or_404(BaseExercise, id=submission_json["exercise_id"])
        form = TeacherCreateAndAssessSubmissionForm(submission_json, exercise=exercise)

        if form.is_valid():
            validated_forms.append(form)
        else:
            return HttpResponseBadRequest(_("The data did not validate. No submissions were saved."))

    # The data validated. Now lets save it.
    for form in validated_forms:
        new_submission = Submission.objects.create(exercise=form.exercise)
        new_submission.submitters = form.cleaned_data.get("students") or form.cleaned_data.get("students_by_student_id")
        new_submission.feedback = form.cleaned_data.get("feedback")
        new_submission.set_points(form.cleaned_data.get("points"), new_submission.exercise.max_points, no_penalties=True)
        new_submission.submission_time = form.cleaned_data.get("submission_time")
        new_submission.grading_time = datetime.now()
        new_submission.grader = form.cleaned_data.get("grader") or teacher
        new_submission.set_ready()
        new_submission.save()

    return HttpResponse("Submissions created successfully.")

@login_required
def add_deadline_rule_deviations(request, course_instance):
    course_instance = CourseInstance.objects.get(id=course_instance)
    has_permission  = course_instance.is_teacher(request.user.get_profile()) or request.user.is_superuser or request.user.is_staff

    if not has_permission:
        # TODO: Missing translation.
        return HttpResponseForbidden("You are not allowed to access this view.")

    if request.method == "POST":
        minutes = request.POST["minutes"]
        for user_id in request.POST.getlist("submitter"):
            for exercise_id in request.POST.getlist("exercise"):
                exercise = BaseExercise.objects.get(id=exercise_id)
                submitter = UserProfile.objects.get(id=user_id)
                try:
                    dl_rule_deviation = DeadlineRuleDeviation.objects.create(exercise=exercise, submitter=submitter, extra_minutes=minutes)
                    dl_rule_deviation.save()
                except IntegrityError:
                    messages.warning(request, "DL deviation already exists for user: " +\
                        str(submitter) + " in exercise: " + str(exercise) +\
                        "! Remove it before trying to add a new one")
        return redirect(list_deadline_rule_deviations, course_instance=course_instance.id)


    form = DeadlineRuleDeviationForm(instance=course_instance)

    return render_to_response("exercise/add_deadline_rule_deviations.html", CourseContext(
        request,
        course_instance=course_instance,
        form=form)
    )

@login_required
def list_deadline_rule_deviations(request, course_instance):
    course_instance = CourseInstance.objects.get(id=course_instance)
    has_permission  = course_instance.is_teacher(request.user.get_profile()) or request.user.is_superuser or request.user.is_staff

    if not has_permission:
        # TODO: Missing translation.
        return HttpResponseForbidden("You are not allowed to access this view.")

    deviations = DeadlineRuleDeviation.objects.filter(exercise__course_module__course_instance=course_instance)

    return render_to_response("exercise/list_deadline_rule_deviations.html", CourseContext(request, course_instance=course_instance, deviations=deviations))

@login_required
def remove_deadline_rule_deviation(request, deadline_rule_deviation_id):
    deviation = DeadlineRuleDeviation.objects.get(id=deadline_rule_deviation_id)
    course_instance = deviation.exercise.get_course_instance()
    has_permission  = course_instance.is_teacher(request.user.get_profile()) or request.user.is_superuser or request.user.is_staff

    if not has_permission:
        # TODO: Missing translation.
        return HttpResponseForbidden("You are not allowed to access this view.")

    deviation.delete()

    return redirect(list_deadline_rule_deviations, course_instance=course_instance.id)
