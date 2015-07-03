import logging

from django.conf import settings
from django.contrib import messages
from django.http.response import Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve

from course.context import CourseContext
from course.decorators import access_resource
from exercise.presentation.score import ScoreBoard
from exercise.presentation.summary import UserCourseSummary, UserExerciseSummary
from exercise.protocol.exercise_page import ExercisePage
from exercise.submission_models import SubmittedFile, Submission
from userprofile.models import UserProfile


logger = logging.getLogger("aplus.exercise")


@access_resource
def profile(request, course_url=None, instance_url=None,
            course=None, course_instance=None):
    """
    A personalized page for a student on the course. The page is intended to
    show how well the student is doing on the course and shortcuts to the
    latest submissions.
    """
    summary = UserCourseSummary(course_instance, request.user)
    profile = UserProfile.get_by_request(request)
    submissions = profile.submissions \
        .filter(exercise__course_module__course_instance=course_instance) \
        .order_by("-id")[:10]
    return render_to_response("exercise/profile.html", CourseContext(
        request,
        course_instance=course_instance,
        course_summary=summary,
        submissions=submissions,
    ))


@access_resource
def user_score(request, course_url=None, instance_url=None,
               course=None, course_instance=None):
    """
    The user score and progress for a course instance.

    On the page, all the exercises of the course instance are organized as a
    schedule. They are primarily organized in a list of course modules which
    are primarily ordered according to their closing times and secondarily to
    their opening times. Inside the course modules the exercises are ordered
    according to their order attribute but in the same time, they are also
    grouped to their categories.
    """
    summary = UserCourseSummary(course_instance, request.user)
    score = ScoreBoard(course_instance, request.user)
    return render_to_response("exercise/user_score.html", CourseContext(
        request,
        course=course,
        course_instance=course_instance,
        course_summary=summary,
        exercise_tree=score.collect_tree(summary),
        visible_categories=score.collect_categories(summary),
    ))


@csrf_exempt
@access_resource
def view_exercise(request, course_url=None, instance_url=None, exercise_id=None,
                  course=None, course_instance=None, exercise=None):
    """
    Displays exercise content and receives exercise submissions.
    
    """
    if request.is_ajax():
        summary = UserExerciseSummary(exercise, request.user)
        return render_to_response('exercise/_exercise_info.html', CourseContext(
            request,
            exercise=exercise,
            course_instance=course_instance,
            exercise_summary=summary,
        ))

    # TODO: add ability to select a group
    students = (UserProfile.get_by_request(request),)
    page = ExercisePage(exercise)

    ok, issues = exercise.is_submission_allowed(students)
    for msg in issues:
        messages.warning(request, msg)

    if request.method == "POST" and ok:
        new_submission = Submission.objects.create_from_post(
            exercise, students, request)
        if new_submission:
            page = exercise.grade(request, new_submission) 
        else:
            messages.error(request,
                _("The submission could not be saved for some reason. "
                  "This might be caused by too long file name. "
                  "The submission was not registered."))
    else:
        page = exercise.load(request, students)

    summary = UserExerciseSummary(exercise, request.user)
    profile = UserProfile.get_by_request(request)
    submissions = exercise.get_submissions_for_student(profile)
    return render_to_response('exercise/exercise.html', CourseContext(
        request,
        exercise=exercise,
        course_instance=course_instance,
        page=page,
        submissions=submissions,
        exercise_summary=summary,
    ))


@access_resource
def view_submission(request, course_url=None, instance_url=None,
                    exercise_id=None, submission_id=None,
                    course=None, course_instance=None,
                    exercise=None, submission=None):

    if submission.is_submitter(request.user):
        profile = UserProfile.get_by_request(request)
    else:
        profile = submission.submitters.first()
    
    submissions = exercise.get_submissions_for_student(profile)
    index = 1 + list(submissions).index(submission)

    summary = UserExerciseSummary(exercise, profile.user)

    return render_to_response("exercise/submission.html", CourseContext(
        request,
        submission=submission,
        exercise=exercise,
        course_instance=course_instance,
        submissions=submissions,
        submission_number=index,
        exercise_summary=summary,
    ))


@access_resource
def view_submitted_file(request, course_url=None, instance_url=None,
                    exercise_id=None, submission_id=None, file_id=None, file_name=None,
                  course=None, course_instance=None,
                  exercise=None, submission=None):
    """
    This view checks if the user has permission to download the file with a given id.
    If the user is not permitted, an error response will be returned. Otherwise the file will
    be served for downloading.

    @param request: HttpRequest object from Django
    @param submitted_file_id: the id for the SubmittedFile model to be downloaded
    """
    file = get_object_or_404(SubmittedFile, id=file_id, submission=submission)
    if file.filename != file_name:
        raise Http404()
    return serve(request, file.file_object.name, settings.MEDIA_ROOT)
