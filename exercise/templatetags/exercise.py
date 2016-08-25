from django import template
from django.db.models import Max, Min
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from cached.content import CachedContent
from cached.points import CachedPoints
from ..models import BaseExercise
from ..presentation.score import collect_tree
from ..presentation.summary import UserCourseSummary


register = template.Library()


class TagUsageError(Exception):
    pass


def _prepare_context(context):
    if not 'instance' in context:
        raise TagUsageError()
    instance = context['instance']
    user = context['request'].user
    if not 'now' in context:
        context['now'] = timezone.now()
    if not 'content' in context:
        context['content'] = CachedContent(instance)
    if not 'points' in context:
        context['points'] = CachedPoints(instance, user, context['content'])
    points = context['points']
    return {
        'now': context['now'],
        'toc': points.full_hierarchy(),
        'categories': points.categories(),
        'is_course_staff': context.get('is_course_staff', False),
    }


@register.inclusion_tag("exercise/_user_results.html", takes_context=True)
def user_results(context):
    return _prepare_context(context)


@register.inclusion_tag("exercise/_user_toc.html", takes_context=True)
def user_toc(context):
    return _prepare_context(context)


@register.inclusion_tag("exercise/_category_points.html", takes_context=True)
def category_points(context):
    return _prepare_context(context)


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


def _progress_data(points, max_points, passed=False, required=None):
    """
    Formats data for progress bar template.
    """
    percentage = 100
    required_percentage = None
    if max_points > 0:
        percentage = int(round(100.0 * points / max_points))
        if required:
            required_percentage = int(round(100.0 * required / max_points))
    return {
        "points": points,
        "max": max_points,
        "percentage": percentage,
        "required": required,
        "required_percentage": required_percentage,
        "passed": passed,
    }


@register.inclusion_tag("exercise/_points_progress.html")
def points_progress(points, max_points, passed=False, required=None):
    return _progress_data(points, max_points, passed, required)


@register.inclusion_tag("exercise/_points_progress.html")
def summary_progress(entry):
    return _progress_data(
        entry['points'],
        entry['max_points'],
        entry['passed'],
        entry['points_to_pass']
    )


@register.inclusion_tag("exercise/_points_badge.html")
def summary_points(entry, classes=None):
    return {
        "classes": classes,
        "points": entry['points'],
        "max": entry['max_points'],
        "required": entry['points_to_pass'],
        "missing_points": entry['points'] < entry['points_to_pass'],
        "passed": entry['passed'],
        "full_score": entry['points'] >= entry['max_points'],
        "submitted": entry['submission_count'] > 0,
    }


@register.inclusion_tag("exercise/_points_badge.html")
def submission_points(submission, classes=None):
    exercise = submission.exercise
    passed = submission.grade >= exercise.points_to_pass
    return {
        "classes": classes,
        "points": submission.grade,
        "max": exercise.max_points,
        "required": exercise.points_to_pass,
        "missing_points": not passed,
        "passed": passed,
        "full_score": submission.grade >= exercise.max_points,
        "submitted": True,
        "status": False if submission.is_graded else submission.status
    }


@register.filter
def max_group_size(course_instance):
    return BaseExercise.objects \
        .filter(course_module__course_instance=course_instance) \
        .aggregate(max=Max('max_group_size'))['max']


@register.filter
def min_group_size(course_instance):
    return BaseExercise.objects \
        .filter(course_module__course_instance=course_instance, max_group_size__gt=1) \
        .aggregate(min=Min('min_group_size'))['min']
