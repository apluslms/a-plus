# Django
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.views.static import serve
from django.template.context import RequestContext
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

# A+
from userprofile.models import UserProfile, StudentGroup
from exercise.exercise_models import BaseExercise, CourseModule
from exercise.submission_models import Submission, SubmittedFile
from exercise.exercise_page import ExercisePage
from exercise.exercise_summary import ExerciseSummary
from exercise.forms import BaseExerciseForm, SubmissionReviewForm
from lib import helpers
from course.context import CourseContext
from django.utils import simplejson

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
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    submissions     = exercise.submissions.all()
    
    return render_to_response("exercise/exercise_submissions.html", 
                              CourseContext(request,
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
    
    return render_to_response("exercise/inspect_submission.html", 
                              CourseContext(request,
                                            submission=submission,
                                            exercise=exercise,
                                            course_instance=exercise.get_course_instance()
                                           ))

@login_required
def add_or_edit_exercise(request, module_id, exercise_id=None):
    """ 
    This page can be used by teachers to add new exercises and edit existing ones.
    """
    module          = get_object_or_404(CourseModule, id=module_id)
    course_instance = module.course_instance
    
    has_permission  = course_instance.is_teacher(request.user.get_profile()) 
    
    if not has_permission:
        return HttpResponseForbidden("You are not allowed to access this view.")
    
    if exercise_id != None:
        exercise = get_object_or_404(module.learning_objects, id=exercise_id).as_leaf_class()
    else:
        exercise = BaseExercise(course_module=module)
    
    if request.method == "POST":
        form = BaseExerciseForm(request.POST, instance=exercise)
        if form.is_valid():
            exercise = form.save()
            messages.success(request, _('The exercise was saved successfully.'))
    else:
        form = BaseExerciseForm(instance=exercise)
    
    return render_to_response("exercise/edit_exercise.html", 
                              CourseContext(request, course_instance=course_instance,
                                                     exercise=exercise,
                                                     form=form
                                             ))


@login_required
def submission_assessment(request, submission_id):
    """
    This view is used for assessing the given exercise submission. When assessing,
    the teacher or assistant may write verbal feedback and give a numeric grade for
    the submission.
    
    @param submission_id: the ID of the submission to assess
    """
    submission      = get_object_or_404(Submission, id=submission_id)
    exercise        = submission.exercise
    
    if exercise.allow_assistant_grading:
        # Both the teachers and assistants are allowed to assess
        has_permission  = exercise.get_course_instance().is_staff(request.user.get_profile()) 
    else:
        # Only teacher is allowed to assess
        has_permission  = exercise.get_course_instance().is_teacher(request.user.get_profile()) 
    
    if not has_permission:
        return HttpResponseForbidden(_("You are not allowed to access this view."))
    
    form            = SubmissionReviewForm()
    if request.method == "POST":
        form        = SubmissionReviewForm(request.POST)
        if form.is_valid():
            try:
                submission.set_points(form.cleaned_data["points"], exercise.max_points)
                submission.grader   = request.user.get_profile()
                submission.feedback = form.cleaned_data["feedback"]
                submission.set_ready()
                submission.save()
                messages.success(request, _("The review was saved successfully."))
                return redirect(inspect_exercise_submission, submission_id=submission.id)
            except:
                messages.error(request, _("Saving review failed. Check that the grade is within allowed boundaries."))
    
    return render_to_response("exercise/submission_assessment.html", 
                              CourseContext(request, 
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

