import datetime
import json
from typing import Any, Dict, Optional, Tuple, Union

from django import template
from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.db import models
from django.template.context import Context
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from course.models import CourseModule
from lib.errors import TagUsageError
from lib.helpers import format_points as _format_points
from ..cache.content import CachedContent
from ..cache.points import CachedPoints
from ..exercise_summary import UserExerciseSummary
from ..models import LearningObjectDisplay, LearningObject, Submission, BaseExercise
from ..reveal_states import ExerciseRevealState


register = template.Library()


def _prepare_now(context):
    if 'now' not in context:
        context['now'] = timezone.now()
    return context['now']


def _prepare_context(context: Context, student: Optional[User] = None) -> CachedPoints:
    if 'instance' not in context:
        raise TagUsageError()
    instance = context['instance']
    _prepare_now(context)
    if 'content' not in context:
        context['content'] = CachedContent(instance)

    def points(user: User, key: str) -> CachedPoints:
        if key not in context:
            context[key] = CachedPoints(instance, user, context['content'], context['is_course_staff'])
        return context[key]
    if student:
        return points(student, 'studentpoints')
    return points(context['request'].user, 'points')


def _get_toc(context, student=None):
    points = _prepare_context(context, student)
    context = context.flatten()
    context.update({
        'modules': points.modules_flatted(),
        'categories': points.categories(),
        'total': points.total(),
        'is_course_staff': context.get('is_course_staff', False),
    })
    return context


def _is_accessible(context, entry, t):
    if t and t > _prepare_now(context):
        return False
    if entry.get('requirements'):
        points = _prepare_context(context)
        module = CourseModule.objects.get(id=entry['id'])
        return module.are_requirements_passed(points)
    return True


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
            entry,_,_,_ = points.find(last.learning_object)
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


def _reveal_rule(exercise: BaseExercise, user: User) -> Tuple[bool, Optional[datetime.datetime]]:
    rule = exercise.active_submission_feedback_reveal_rule
    state = ExerciseRevealState(exercise, user)
    is_revealed = rule.is_revealed(state)
    reveal_time = rule.get_reveal_time(state)
    return is_revealed, reveal_time


def _points_data( # pylint: disable=too-many-locals
        obj: Union[UserExerciseSummary, Submission, Dict[str, Any]],
        user: User,
        classes: Optional[str] = None,
        is_staff: bool = False,
        known_revealed: Optional[bool] = None,
        ) -> Dict[str, Any]:
    reveal_time = None
    is_revealed = None
    if known_revealed is not None:
        is_revealed = known_revealed
    elif is_staff:
        is_revealed = True
    if isinstance(obj, UserExerciseSummary):
        exercise = obj.exercise
        if is_revealed is None:
            is_revealed, reveal_time = _reveal_rule(exercise, user)
        data = {
            'points': obj.get_points() if is_revealed else 0,
            'formatted_points': _format_points(obj.get_points(), is_revealed, False),
            'max': exercise.max_points,
            'difficulty': exercise.difficulty,
            'required': exercise.points_to_pass,
            'confirm_the_level': exercise.category.confirm_the_level,
            'missing_points': obj.is_missing_points() if is_revealed else False,
            'passed': obj.is_passed() if is_revealed else False,
            'full_score': obj.is_full_points() if is_revealed else False,
            'submitted': obj.is_submitted(),
            'graded': obj.is_graded(),
            'official': not obj.is_unofficial(),
            'exercise_page': True,
            'feedback_revealed': is_revealed,
        }
    elif isinstance(obj, Submission):
        exercise = obj.exercise
        if is_revealed is None:
            is_revealed, reveal_time = _reveal_rule(exercise, user)
        data = {
            'points': obj.grade if is_revealed else 0,
            'formatted_points': _format_points(obj.grade, is_revealed, False),
            'max': exercise.max_points,
            'difficulty': exercise.difficulty,
            'required': exercise.points_to_pass,
            'confirm_the_level': exercise.category.confirm_the_level,
            'missing_points': (obj.grade < exercise.points_to_pass) if is_revealed else False,
            'passed': (obj.grade >= exercise.points_to_pass) if is_revealed else False,
            'full_score': (obj.grade >= exercise.max_points) if is_revealed else False,
            'submitted': True,
            'graded': obj.is_graded,
            'official': obj.status != Submission.STATUS.UNOFFICIAL,
            'feedback_revealed': is_revealed,
        }
        if not obj.is_graded and (
                    not exercise.category.confirm_the_level
                    or obj.status != Submission.STATUS.WAITING
                ):
            data['status'] = obj.status
    else:
        points = obj.get('points', 0)
        max_points = obj.get('max_points', 0)
        required = obj.get('points_to_pass', 0)
        data = {
            'points': points,
            'formatted_points': obj.get('formatted_points', '0'),
            'max': max_points,
            'difficulty': obj.get('difficulty', ''),
            'required': required,
            'confirm_the_level': obj.get('confirm_the_level', False),
            'missing_points': points < required,
            'passed': obj.get('passed', True),
            'full_score': points >= max_points,
            'submitted': obj.get('submission_count', 0) > 0,
            'graded': obj.get('graded', True),
            'status': obj.get('submission_status', False),
            'unconfirmed': obj.get('unconfirmed', False),
            'official': not obj.get('unofficial', False),
            'confirmable_points': obj.get('confirmable_points', False),
            'feedback_revealed': obj.get('feedback_revealed', True),
        }
        reveal_time = obj.get('feedback_reveal_time')
    percentage = 0
    required_percentage = None
    if data['max'] > 0:
        percentage = int(round(100.0 * data['points'] / data['max']))
        if data['required']:
            required_percentage = int(round(100.0 * data['required'] / data['max']))
    feedback_hidden_description = None
    if not data.get('feedback_revealed'):
        if isinstance(obj, dict) and obj.get('type') != 'exercise':
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


@register.inclusion_tag("exercise/_points_progress.html", takes_context=True)
def points_progress(
        context: Context,
        obj: Union[UserExerciseSummary, Submission, Dict[str, Any]],
        is_revealed: Optional[bool] = None,
        ) -> Dict[str, Any]:
    return _points_data(obj, context['request'].user, None, context['is_course_staff'], is_revealed)


@register.inclusion_tag("exercise/_points_badge.html", takes_context=True)
def points_badge(
        context: Context,
        obj: Union[UserExerciseSummary, Submission, Dict[str, Any]],
        classes: Optional[str] = None,
        is_revealed: Optional[bool] = None,
        ) -> Dict[str, Any]:
    return _points_data(obj, context['request'].user, classes, context['is_course_staff'], is_revealed)


@register.simple_tag
def format_points(points: int, is_revealed: bool, is_container: bool) -> str:
    return _format_points(points, is_revealed, is_container)


@register.simple_tag(takes_context=True)
def max_group_size(context):
    points = _prepare_context(context)
    return points.total()['max_group_size']


@register.simple_tag(takes_context=True)
def min_group_size(context):
    points = _prepare_context(context)
    return points.total()['min_group_size']


@register.simple_tag(takes_context=True)
def module_accessible(context, entry):
    t = entry.get('reading_opening_time')
    if t:
        return _is_accessible(context, entry, t)
    return exercise_accessible(context, entry)


@register.simple_tag(takes_context=True)
def exercise_accessible(context, entry):
    t = entry.get('opening_time')
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
