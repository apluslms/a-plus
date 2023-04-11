import json
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from exercise.models import BaseExercise, Submission
from lib.helpers import extract_form_errors
from ..submission_forms import BatchSubmissionCreateAndReviewForm


def create_submissions(instance, admin_profile, json_text):
    """
    Batch creates submissions and feedback from formatted JSON.
    """
    try:
        submissions_json = json.loads(json_text)
    except Exception as e:
        return [format_lazy(
            _('EXCEPTION_PARSING_SUBMISSION_JSON -- {error!s}'),
            error=e,
        )]

    if isinstance(submissions_json, dict):
        if "objects" not in submissions_json:
            return [_('JSON_FIELD_MISSING_OBJECTS')]
        submissions_json = submissions_json["objects"]
    if not isinstance(submissions_json, list):
        return [_('JSON_INVALID_EXPECTED_LIST')]

    errors = []
    validated_forms = []
    count = 0
    for submission_json in submissions_json:
        count += 1
        if "exercise_id" not in submission_json:
            errors.append(
                format_lazy(
                    _('JSON_ERROR_MISSING_FIELD_EXERCISE_ID -- {count:d}'),
                    count=count,
                )
            )
            continue

        exercise = BaseExercise.objects.filter(
            id=submission_json["exercise_id"],
            course_module__course_instance=instance).first()
        if not exercise:
            errors.append(
                format_lazy(
                    _('JSON_ERROR_UNKNOWN_EXERCISE_ID -- {id:d}, {count:d}'),
                    id=submission_json["exercise_id"],
                    count=count,
                )
            )
            continue

        # Use form to parse and validate object data.
        form = BatchSubmissionCreateAndReviewForm(submission_json,
            exercise=exercise)
        if form.is_valid():
            validated_forms.append(form)
        else:
            errors.append(
                format_lazy(
                    _('JSON_ERROR_OBJECT_INVALID_FIELDS -- {ordinal:d}, {errors}'),
                    ordinal=count,
                    errors='\n '.join(extract_form_errors(form))
                )
            )

    if not errors:
        for form in validated_forms:
            sub = Submission.objects.create(exercise=form.exercise)
            sub.submitters.set(form.cleaned_students)
            sub.feedback = form.cleaned_data.get("feedback")
            sub.set_points(form.cleaned_data.get("points"),
                sub.exercise.max_points, no_penalties=True)
            sub.submission_time = form.cleaned_data.get("submission_time")
            sub.grading_time = timezone.now()
            sub.grader = form.cleaned_data.get("grader") or admin_profile
            sub.set_ready()
            sub.save()

    return errors
