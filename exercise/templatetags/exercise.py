import json
from django import template
from django.db.models import Max, Min
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from course.models import CourseModule
from lib.errors import TagUsageError
from ..cache.content import CachedContent
from ..cache.points import CachedPoints
from ..exercise_summary import UserExerciseSummary
from ..models import LearningObjectDisplay, LearningObject, Submission, BaseExercise


register = template.Library()


def _prepare_now(context):
    if not 'now' in context:
        context['now'] = timezone.now()
    return context['now']


def _prepare_context(context, student=None):
    if not 'instance' in context:
        raise TagUsageError()
    instance = context['instance']
    _prepare_now(context)
    if not 'content' in context:
        context['content'] = CachedContent(instance)
    def points(user, key):
        if not key in context:
            context[key] = CachedPoints(instance, user, context['content'])
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
def user_results(context, student=None):
    values = _get_toc(context, student)
    values['total_json'] = json.dumps(values['total'])
    if student:
        values['is_course_staff'] = False
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
def max_submissions(exercise, user_profile):
    return exercise.max_submissions_for_student(user_profile)


@register.filter
def percent(decimal):
    return int(decimal * 100)


@register.filter
def submission_status(status):
    return Submission.STATUS[status]


def _points_data(obj, classes=None):
    if isinstance(obj, UserExerciseSummary):
        exercise = obj.exercise
        data = {
            'points': obj.get_points(),
            'max': exercise.max_points,
            'difficulty': exercise.difficulty,
            'required': exercise.points_to_pass,
            'confirm_the_level': exercise.category.confirm_the_level,
            'missing_points': obj.is_missing_points(),
            'passed': obj.is_passed(),
            'full_score': obj.is_full_points(),
            'submitted': obj.is_submitted(),
            'graded': obj.is_graded(),
            'official': not obj.is_unofficial(),
            'exercise_page': True,
        }
    elif isinstance(obj, Submission):
        exercise = obj.exercise
        data = {
            'points': obj.grade,
            'max': exercise.max_points,
            'difficulty': exercise.difficulty,
            'required': exercise.points_to_pass,
            'confirm_the_level': exercise.category.confirm_the_level,
            'missing_points': obj.grade < exercise.points_to_pass,
            'passed': obj.grade >= exercise.points_to_pass,
            'full_score': obj.grade >= exercise.max_points,
            'submitted': True,
            'graded': obj.is_graded,
            'official': obj.status != Submission.STATUS.UNOFFICIAL,
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
        }
    percentage = 0
    required_percentage = None
    if data['max'] > 0:
        percentage = int(round(100.0 * data['points'] / data['max']))
        if data['required']:
            required_percentage = int(round(100.0 * data['required'] / data['max']))
    data.update({
        'classes': classes,
        'percentage': percentage,
        'required_percentage': required_percentage,
    })
    return data


@register.inclusion_tag("exercise/_points_progress.html")
def points_progress(obj):
    return _points_data(obj)


@register.inclusion_tag("exercise/_points_badge.html")
def points_badge(obj, classes=None):
    return _points_data(obj, classes)


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
    else:
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
def exercise_text_stats(context, exercise):
    if not 'instance' in context:
        raise TagUsageError()
    instance = context['instance']

    if not 'student_count' in context:
        context['student_count'] = instance.students.count()
    total = context['student_count']

    if isinstance(exercise, int):
        num = instance.students.filter(submissions__exercise_id=exercise).distinct().count()
    else:
        num = exercise.number_of_submitters() if exercise else 0
    return {
        "number": num,
        "percentage": int(100 * num / total) if total else 0,
    }


@register.simple_tag
def get_format_info(format):
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
