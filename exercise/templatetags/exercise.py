from django import template
from django.db.models import Max, Min
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from cached.content import CachedContent
from cached.points import CachedPoints
from lib.errors import TagUsageError
from ..exercise_summary import UserExerciseSummary
from ..models import LearningObjectDisplay, LearningObject, Submission, BaseExercise


register = template.Library()


def _prepare_context(context):
    if not 'instance' in context:
        raise TagUsageError()
    instance = context['instance']
    if not 'now' in context:
        context['now'] = timezone.now()
    if not 'content' in context:
        context['content'] = CachedContent(instance)
    if not 'points' in context:
        user = context['request'].user
        context['points'] = CachedPoints(instance, user, context['content'])
    return context['points']


def _get_toc(context):
    points = _prepare_context(context)
    return {
        'now': context['now'],
        'toc': points.full_hierarchy(),
        'categories': points.categories(),
        'is_course_staff': context.get('is_course_staff', False),
    }


@register.inclusion_tag("exercise/_user_results.html", takes_context=True)
def user_results(context):
    return _get_toc(context)


@register.inclusion_tag("exercise/_user_toc.html", takes_context=True)
def user_toc(context):
    return _get_toc(context)


@register.inclusion_tag("exercise/_user_last.html", takes_context=True)
def user_last(context):
    user = context['request'].user
    points = _prepare_context(context)
    if user.is_authenticated():
        last = LearningObjectDisplay.objects.filter(
            profile=user.userprofile,
            learning_object__status=LearningObject.STATUS.READY,
            learning_object__course_module__course_instance=context['instance'],
        ).select_related('learning_object').order_by('-timestamp').first()
        if last:
            _,entry,_ = points.find(last.learning_object)
            return {
                'last': entry,
                'last_time': last.timestamp,
            }
    return {
        'begin': points.begin(),
    }


@register.inclusion_tag("exercise/_category_points.html", takes_context=True)
def category_points(context):
    return _get_toc(context)


@register.inclusion_tag("exercise/_submission_list.html", takes_context=True)
def latest_submissions(context):
    submissions = context["profile"].submissions \
        .filter(exercise__course_module__course_instance=context["instance"]) \
        .order_by("-id")[:10]
    return {
        "submissions": submissions,
        "title": _("Latest submissions"),
        "empty": _("No submissions for this course."),
    }


@register.filter
def max_submissions(exercise, user_profile):
    return exercise.max_submissions_for_student(user_profile)


@register.filter
def percent(decimal):
    return int(decimal * 100)


def _points_data(obj, classes=None):
    if isinstance(obj, UserExerciseSummary):
        data = {
            'points': obj.get_points(),
            'max': obj.get_max_points(),
            'required': obj.get_required_points(),
            'missing_points': obj.is_missing_points(),
            'passed': obj.is_passed(),
            'full_score': obj.is_full_points(),
            'submitted': obj.is_submitted(),
        }
    elif isinstance(obj, Submission):
        exercise = obj.exercise
        data = {
            'points': obj.grade,
            'max': exercise.max_points,
            'required': exercise.points_to_pass,
            'missing_points': obj.grade < exercise.points_to_pass,
            'passed': obj.grade >= exercise.points_to_pass,
            'full_score': obj.grade >= exercise.max_points,
            'submitted': True,
            'status': False if obj.is_graded else obj.status
        }
    else:
        data = {
            'points': obj['points'],
            'max': obj['max_points'],
            'required': obj['points_to_pass'],
            'missing_points': obj['points'] < obj['points_to_pass'],
            'passed': obj['passed'],
            'full_score': obj['points'] >= obj['max_points'],
            'submitted': obj['submission_count'] > 0,
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


@register.assignment_tag(takes_context=True)
def max_group_size(context):
    points = _prepare_context(context)
    return points.total()['max_group_size']


@register.assignment_tag(takes_context=True)
def min_group_size(context):
    points = _prepare_context(context)
    return points.total()['min_group_size']
