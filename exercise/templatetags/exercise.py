import json
from typing import Any, Dict, Iterable, Optional, Union

from django import template
from django.contrib.auth.models import User
from django.db import models
from django.template.context import Context
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from course.models import CourseInstance, CourseModule
from lib.errors import TagUsageError
from lib.helpers import format_points as _format_points, is_ajax as _is_ajax
from userprofile.models import UserProfile
from ..cache.points import (
    CachedPoints,
    CachedPointsData,
    CategoryPoints,
    LearningObjectPoints,
    ModulePoints,
    SubmissionEntry,
    ExercisePoints,
)
from ..models import LearningObjectDisplay, LearningObject, Submission, BaseExercise


register = template.Library()

def _prepare_now(context):
    if 'now' not in context:
        context['now'] = timezone.now()
    return context['now']


def _prepare_context(context: Context, student: Optional[User] = None) -> CachedPoints:
    _prepare_now(context)

    if student is None:
        return context["points"]

    if student.id != context["studentpoints"].user.id:
        if 'instance' not in context:
            raise TagUsageError()
        instance = context['instance']

        context["studentpoints"] = CachedPoints(instance, student, context['is_course_staff'])

    return context["studentpoints"]


def _get_toc(context, student=None):
    points = _prepare_context(context, student)

    context = context.flatten()
    context.update({
        'modules': points.modules_flatted(),
        'categories': points.categories(),
        'total': points.total().as_dict(),
        'is_course_staff': context.get('is_course_staff', False),
    })
    return context


def _is_accessible(context, entry, t):
    if t and t > _prepare_now(context):
        return False
    if entry.requirements:
        points = _prepare_context(context)
        module = CourseModule.objects.get(id=entry['id'])
        return module.are_requirements_passed(points)
    return True


@register.simple_tag
def check_exercise_deadline_extensions(children, entry_name, is_module_specific=None):
    output = ''
    exercise_count = 0
    for exercise in children:
        # Module specific ToC page
        if (
          is_module_specific
          and exercise.parent
          and exercise.parent.name == entry_name
          and exercise.personal_deadline
        ):
            exercise_count += 1
        # ToC page
        elif exercise.type != 'level' and not exercise.is_empty and exercise.submittable:
            if exercise.parent and exercise.parent.name == entry_name and exercise.personal_deadline:
                exercise_count += 1
    if exercise_count > 0:
        output = format_lazy(_('PERSONAL_EXTENDED_DEADLINE_PLURAL -- {count}'), count=exercise_count)
    return mark_safe(output)


@register.inclusion_tag("exercise/_user_results.html", takes_context=True)
def user_results(context: Context, student: Optional[User] = None) -> Dict[str, Any]:
    values = _get_toc(context, student)
    values['total_json'] = json.dumps(values['total'])
    if values['is_course_staff']:
        instance = context['instance']
        values['student_count'] = instance.students.count()
        counts = (instance.students
            .filter(submissions__exercise__course_module__course_instance=instance)
            .values('submissions__exercise_id')
            .annotate(count=models.Count('submissions__submitters', distinct=True))
            .order_by()
        )
        values['exercise_submitter_counts'] = {row['submissions__exercise_id']: row['count'] for row in counts}
    return values


@register.inclusion_tag("exercise/_user_toc.html", takes_context=True)
def user_toc(context, student=None):
    return _get_toc(context, student)


@register.inclusion_tag("exercise/_user_last.html", takes_context=True)
def user_last(context):
    user = context['request'].user
    points = _prepare_context(context)
    if user.is_authenticated:
        last = LearningObjectDisplay.objects.filter(
            profile=user.userprofile,
            learning_object__status=LearningObject.STATUS.READY,
            learning_object__course_module__course_instance=context['instance'],
        ).select_related('learning_object').order_by('-timestamp').first()
        if last:
            entry = points.get_exercise(last.learning_object.id)
            return {
                'last': entry,
                'last_time': last.timestamp,
            }
    return {
        'begin': points.begin(),
        'instance': context['instance'],
    }


@register.inclusion_tag("exercise/_category_points.html", takes_context=True)
def category_points(context, student=None):
    return _get_toc(context, student)


@register.inclusion_tag("exercise/_submission_list.html", takes_context=True)
def latest_submissions(context):
    submissions = context["profile"].submissions \
        .filter(exercise__course_module__course_instance=context["instance"]) \
        .order_by("-id")[:10]
    return {
        "submissions": submissions,
        "title": _('LATEST_SUBMISSIONS'),
        "empty": _('NO_SUBMISSIONS_FOR_COURSE'),
    }


@register.filter
def percent(decimal):
    return int(decimal * 100)


@register.filter
def submission_status(status):
    return Submission.STATUS[status]


@register.filter
def compared_submission_param(compared_submission) -> str:
    param = 'compare_to='
    if isinstance(compared_submission, SubmissionEntry):
        return param + str(compared_submission.id)
    return param + compared_submission


AnyPointsEntry = Union[
    CachedPointsData,
    ModulePoints,
    CategoryPoints,
    LearningObjectPoints,
    ExercisePoints,
    SubmissionEntry,
]

def _points_data(
        obj: AnyPointsEntry,
        classes: Optional[str] = None,
        ) -> Dict[str, Any]:
    reveal_time = None

    # All the different cached points entries
    if isinstance(obj, ExercisePoints):
        points = obj.official_points
    else:
        points = obj.points

    max_points = getattr(obj, 'max_points',  0)
    required = getattr(obj, 'points_to_pass',  0)
    module_goal_points = getattr(obj, 'module_goal_points', None)
    if module_goal_points is not None:
        module_goal_percentage = (module_goal_points / max_points) * 100
    else:
        module_goal_percentage = None
    module_goal_achieved = (
        module_goal_points
        and points >= module_goal_points
    )

    data = {
        'points': points,
        'formatted_points': getattr(obj, 'formatted_points',  '0'),
        'max': max_points,
        'difficulty': getattr(obj, 'difficulty',  ''),
        'required': required,
        'confirm_the_level': getattr(obj, 'confirm_the_level',  False),
        'missing_points': points < required,
        'passed': getattr(obj, 'passed',  True),
        'full_score': points >= max_points,
        'submitted': getattr(obj, 'submission_count',  0) > 0,
        'graded': getattr(obj, 'graded',  True),
        'unconfirmed': getattr(obj, 'unconfirmed',  False),
        'official': not getattr(obj, 'unofficial',  False),
        'unofficial_submission_type': getattr(obj, 'unofficial_submission_type', None),
        'confirmable_points': getattr(obj, 'confirmable_points',  False),
        'feedback_revealed': getattr(obj, 'feedback_revealed',  True),
        'module_goal_points': module_goal_points,
        'module_goal_percentage': module_goal_percentage,
        'module_goal_achieved': module_goal_achieved,
    }
    reveal_time = getattr(obj, 'feedback_reveal_time', None)

    if isinstance(obj, SubmissionEntry) and not data['graded']:
        data['submission_status'] = obj.status
    elif isinstance(obj, LearningObjectPoints):
        data['exercise_page'] = True

    percentage = 0
    required_percentage = None
    if data['max'] > 0:
        percentage = int(round(100.0 * data['points'] / data['max']))
        if data['required']:
            required_percentage = int(round(100.0 * data['required'] / data['max']))
    feedback_hidden_description = None
    if not data.get('feedback_revealed'):
        if isinstance(obj, (SubmissionEntry, CategoryPoints, ModulePoints, CachedPointsData)):
            feedback_hidden_description = _('RESULTS_OF_SOME_ASSIGNMENTS_ARE_CURRENTLY_HIDDEN')
        elif reveal_time is not None:
            formatted_time = date_format(timezone.localtime(reveal_time), "DATETIME_FORMAT")
            feedback_hidden_description = format_lazy(
                _('RESULTS_WILL_BE_REVEALED -- {time}'),
                time=formatted_time,
            )
        else:
            feedback_hidden_description = _('RESULTS_ARE_CURRENTLY_HIDDEN')
    data.update({
        'classes': classes,
        'percentage': percentage,
        'required_percentage': required_percentage,
        'feedback_hidden_description': feedback_hidden_description,
    })
    return data


@register.inclusion_tag("exercise/_points_progress.html")
def points_progress(
        obj: Union[CachedPointsData, ModulePoints, CategoryPoints],
        points_goal_enabled: Optional[bool] = None,
        ) -> Dict[str, Any]:
    points_data = _points_data(obj, None)
    points_data['points_goal_enabled'] = points_goal_enabled
    return points_data


@register.inclusion_tag("exercise/_points_badge.html")
def points_badge(
        obj: Union[ModulePoints, LearningObjectPoints, ExercisePoints, SubmissionEntry],
        classes: Optional[str] = None,
        ) -> Dict[str, Any]:
    return _points_data(obj, classes)


@register.simple_tag
def format_points(points: int, is_revealed: bool, is_container: bool) -> str:
    return _format_points(points, is_revealed, is_container)


@register.simple_tag(takes_context=True)
def module_accessible(context, entry):
    t = entry.reading_opening_time
    if t:
        return _is_accessible(context, entry, t)
    return exercise_accessible(context, entry)


@register.simple_tag(takes_context=True)
def exercise_accessible(context, entry):
    t = entry.opening_time
    return _is_accessible(context, entry, t)


@register.simple_tag
def get_grading_errors(submission):
    if not isinstance(submission.grading_data, dict):
        return ""
    grading_data = submission.grading_data.get('grading_data')
    if not isinstance(grading_data, str):
        return ""
    if grading_data.startswith('<pre>'):
        return grading_data[5:-6]
    try:
        return json.loads(grading_data).get('errors', "")
    except (AttributeError, TypeError, ValueError):
        return ""


@register.inclusion_tag("exercise/_text_stats.html", takes_context=True)
def exercise_text_stats(context: Context, exercise: Union[int, BaseExercise]) -> Dict[str, Any]:
    if 'instance' not in context:
        raise TagUsageError()
    instance = context['instance']

    if 'student_count' not in context:
        context['student_count'] = instance.students.count()
    total = context['student_count']

    if isinstance(exercise, int):
        if 'exercise_submitter_counts' in context:
            num = context['exercise_submitter_counts'].get(exercise, 0)
        else:
            num = instance.students.filter(submissions__exercise_id=exercise).distinct().count()
    else:
        num = exercise.number_of_submitters() if exercise else 0
    return {
        "number": num,
        "percentage": int(100 * num / total) if total else 0,
    }


@register.simple_tag
def get_format_info(format): # pylint: disable=redefined-builtin
    format_infos = {
        'json' : {
            'name': 'json',
            'verbose_name': 'JSON',
        },
        'csv': {
            'name': 'csv',
            'verbose_name': 'CSV',
        },
        'excel.csv': {
            'name': 'excel.csv',
            'verbose_name': _('EXCEL_COMPATIBLE_CSV'),
        },
    }
    try:
        return format_infos[format]
    except KeyError as e:
        raise RuntimeError('Invalid format: \'{}\''.format(format)) from e


@register.simple_tag
def get_format_info_list(formats):
    return [get_format_info(format) for format in formats.split()]


@register.simple_tag
def get_zip_info(type): # pylint: disable=redefined-builtin
    zip_infos = {
        'all' : {
            'best': 'no',
            'verbose_name': _('ALL_SUBMISSIONS'),
        },
        'best': {
            'best': 'yes',
            'verbose_name': _('BEST_SUBMISSIONS'),
        },
    }
    try:
        return zip_infos[type]
    except KeyError as e:
        raise RuntimeError('Invalid zip type: \'{}\''.format(type)) from e


@register.simple_tag
def get_zip_info_list(types):
    return [get_zip_info(type) for type in types.split()]


@register.simple_tag
def get_regrade_info(index):
    regrade_infos = {
        'all' : {
            'name': 'all',
            'verbose_name': _('ALL'),
        },
        'incomplete': {
            'name': 'incomplete',
            'verbose_name': _('INCOMPLETE'),
        },
    }
    try:
        return regrade_infos[index]
    except KeyError as e:
        raise RuntimeError("Invalid format: '{}'".format(index)) from e


@register.simple_tag
def get_regrade_info_list(options):
    return [get_regrade_info(index) for index in options.split()]


@register.simple_tag(takes_context=True)
def is_ajax(context: Context) -> bool:
    return _is_ajax(context['request'])


@register.inclusion_tag('exercise/staff/_deviationslink.html')
def adddeviationsbutton(
        instance: CourseInstance,
        module: Optional[Union[Dict[str, Any], CourseModule]] = None,
        exercise: Optional[Union[Dict[str, Any], LearningObject]] = None,
        submitters: Optional[Union[User, UserProfile, Iterable[User], Iterable[UserProfile]]] = None,
        ):
    def user_id(user):
        return str(user.user_id if isinstance(user, UserProfile) else user.id)

    if submitters is None:
        submitter_str = None
    elif isinstance(submitters, (User, UserProfile)):
        submitter_str = user_id(submitters)
    else:
        submitter_str = ",".join(user_id(s) for s in submitters)

    return {
        "instance": instance,
        "module": module,
        "exercise": exercise,
        "submitters": submitter_str,
    }
