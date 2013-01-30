# Python
import logging

from lib.BeautifulSoup import BeautifulSoup

# Django
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, \
    HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.views.static import serve
from django.template.context import RequestContext
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.validators import URLValidator

# A+
from userprofile.models import UserProfile, StudentGroup
from exercise.exercise_models import BaseExercise, CourseModule, \
    LearningObjectCategory
from exercise.submission_models import Submission, SubmittedFile
from exercise.exercise_page import ExercisePage
from exercise.exercise_summary import ExerciseSummary
from exercise.forms import BaseExerciseForm
from lib import helpers
from course.context import CourseContext
from django.utils import simplejson

@login_required
@csrf_exempt
def view_exercise(request, exercise_id, template="exercise/view_exercise.html"):
    """ 
    Displays a particular exercise. If the exercise is requested with a HTTP POST request, 
    the view will try to submit the exercise to the exercise service. 
    
    @param request: HttpRequest from Django
    @param exercise_id: the id of the exercise model to display 
    """

    # Load the exercise as an instance of its leaf class
    exercise            = get_object_or_404(BaseExercise, id=exercise_id).as_leaf_class()
    students            = StudentGroup.get_students_from_request(request)
    submissions         = exercise.get_submissions_for_student(request.user.get_profile())
    is_post             = request.method == "POST"
    
    is_allowed, issues  = exercise.is_submission_allowed(students)
    
    for error in issues:
       messages.warning(request, error)
    
    # FIXME: remove support for custom forms
    form = None
    
    if is_post and is_allowed:
        # This is a successful submission, so we handle submitting the form
        return _handle_submission(request, exercise, students, form, submissions)
    
    try:
        # Try retrieving the exercise page
        submission_url  = exercise.get_submission_url_for_students(students)
        page            = exercise.get_page(submission_url)
    
    except Exception as e:
        # Retrieving page failed, create an empty page and display an error
        page            = ExercisePage(exercise=exercise)
        messages.error( request, _('Connecting to the exercise service '
                                   'failed!'))
        logging.exception(e)
    
    exercise_summary    = ExerciseSummary(exercise, request.user)
    
    return render_to_response(template,
                              CourseContext(request,
                                            exercise=exercise,
                                            course_instance=exercise.course_module.course_instance,
                                            page=page,
                                            form=form, 
                                            submissions=submissions,
                                            exercise_summary=exercise_summary
                                            ))


def _handle_submission(request, exercise, students, form, submissions):
    """
    This method takes care of saving a new_submission locally and 
    sending it to an exercise service for assessment. 
    
    @param request: HttpRequest from Django
    @param exercise: an instance of an exercise class this submission is for
    @param students: a QuerySet of UserProfile objects that are submitting the exercise
    @param form: an instance of a Form class or None if there are no questions for the exercise
    @param submissions: previous submissions for the submitting user to the same exercise
    """
    error = False
    response_page = ExercisePage(exercise)

    new_submission                  = Submission.objects.create(exercise=exercise)
    new_submission.submitters       = students
    
    # Save the POST parameters from the new_submission in 
    # a list of tuples [(key1, value1), (key2, value2)].
    # By using tuples inside lists we allow two parameters 
    # with the same name, which is not possible with dicts.
    new_submission.submission_data  = helpers.query_dict_to_list_of_tuples(request.POST)
    
    try:
        # Add all submitted files to the new submission as SubmittedFile
        # objects
        new_submission.add_files( request.FILES )
    except DatabaseError as e:
        messages.error(request, _("The submitted files could not be saved for "
                                  "some reason. This might be caused by too "
                                  "long file name. The submission was not "
                                  "registered."))
        logging.exception(e)
        error = True

    if not error:
        try:
            # Try submitting the submission to the exercise service. The submission
            # is done with a multipart POST request that contains all the files and
            # POST parameters sent by the user.
            response_page               = new_submission.submit_to_service()
        except Exception, e:
            # TODO: pokemon error handling
            # TODO: Retrieving the grading failed. An error report should be sent
            # to administrators
            messages.error(request, _('Connecting to the assessment server '
                                      'failed! The submission was not '
                                      'registered.'))
            logging.exception(e)
    
    if response_page.is_accepted:
        new_submission.feedback     = response_page.content
        new_submission.set_waiting()
        
        if response_page.is_graded:
            # Check if service gave max_points and if it's sane.
            if (response_page.max_points != None
                and not (exercise.max_points != 0
                         and response_page.max_points == 0)
                and response_page.points <= response_page.max_points):
                new_submission.set_points(response_page.points,
                                          response_page.max_points)
                new_submission.set_ready()

                # Add a success message and redirect the user to view the
                # submission
                messages.success(request,
                        _('The exercise was submitted and graded '
                          'successfully. Your points: %d/%d.')
                        % (new_submission.grade,
                           new_submission.exercise.max_points))
            else:
                new_submission.set_error()
                messages.error(request, _("The response from the assessment "
                                          "service was erroneous."))

        else:
            messages.success(request, _('The exercise was submitted successfully and is now waiting to be graded.'))
        
        new_submission.save()
        return redirect(new_submission.get_absolute_url())
    
    else:
        # Delete the unsuccessful submission
        new_submission.delete()
        
        exercise_summary    = ExerciseSummary(exercise, request.user)
        instance            = exercise.course_module.course_instance
        
        # Add a message to the user's message queue
        messages.warning(request, _('The exercise could not be graded. Please check the page below for errors.'))
        return render_to_response("exercise/view_exercise.html", 
                                  CourseContext(request, 
                                                exercise=exercise, 
                                                course_instance=instance,
                                                page=response_page, 
                                                form=form, 
                                                submissions=submissions,
                                                exercise_summary=exercise_summary
                                               ))


@login_required
def view_submission(request, submission_id):
    # Find all submissions for this user
    submission      = get_object_or_404(Submission, id=submission_id)

    if not request.user.get_profile() in submission.submitters.all():
        # Note that we do not want to use submission.check_user_permission here
        # because that would allow staff-like users access this view. However
        # staff-like users should use the
        # staff_views.inspect_exercise_submission instead because some of the
        # stuff in this view wouldn't make sense to a staff-like user.

        # TODO: Yet another repeation of this error (most of them are in
        # course.views)
        return HttpResponseForbidden("You are not allowed "
                                     "to access this view.")

    exercise        = submission.exercise
    submissions     = exercise.get_submissions_for_student(
                                                    request.user.get_profile())
    index           = 1 + list(submissions).index(submission)
    
    exercise_summary= ExerciseSummary(exercise, request.user)
    
    return render_to_response("exercise/view_submission.html", 
                              CourseContext(request,
                                            submission=submission,
                                            exercise=submission.exercise,
                                            course_instance=exercise.course_module.course_instance,
                                            submissions=submissions,
                                            submission_number=index,
                                            exercise_summary=exercise_summary
                                           ))


# TODO: This is not used anymore and should be removed.
@login_required
def toggle_category_visibility(request, category_id):
    category_id = int(category_id)
    category = get_object_or_404(LearningObjectCategory, id=category_id)
    profile = request.user.get_profile()

    if profile in category.hidden_to.all():
        category.hidden_to.remove(profile)
    else:
        category.hidden_to.add(profile)

    if request.GET.has_key("next"):
        next = request.GET["next"]
    else:
        next = category.course_instance.get_absolute_url()

    return HttpResponseRedirect(next)


######################################################################
# Functions for handling submitted files for exercises
######################################################################
@login_required
def view_submitted_file(request, submitted_file_id):
    """ 
    This view checks if the user has permission to download the file with a given id. 
    If the user is not permitted, an error response will be returned. Otherwise the file will
    be served for downloading.
    
    @param request: HttpRequest object from Django
    @param submitted_file_id: the id for the SubmittedFile model to be downloaded 
    """
    file = get_object_or_404(SubmittedFile, id=submitted_file_id)
    
    if file.submission.check_user_permission(request.user.get_profile()):
        return serve(request, file.file_object.name, settings.MEDIA_ROOT)
    
    return HttpResponseForbidden(_("Your are not allowed to access this file."))

