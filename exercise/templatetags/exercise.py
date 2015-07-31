from django import template
from django.template.loader import render_to_string


register = template.Library()


@register.filter
def exercise_summary_classes(exercise_summary):
    classes = []
    if not exercise_summary.is_passed():
        classes.append("btn-danger")
    elif exercise_summary.is_submitted():
        if exercise_summary.is_full_points():
            classes.append("btn-success")
        else:
            classes.append("btn-warning")
    return " ".join(classes)


@register.filter
def max_submissions(exercise, user_profile):
    return exercise.max_submissions_for_student(user_profile)


@register.filter
def percent(decimal):
    return int(decimal * 100)


@register.filter
def students(profiles):
    return ", ".join(
        "{} ({})".format(
            profile.user.get_full_name(),
            profile.student_id if profile.student_id else profile.user.username
        ) for profile in profiles
    )


def _progress_data(points, max_points, passed=False, required=None):
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
        "passed": passed,
        "required": required,
        "required_percentage": required_percentage,
    }


@register.inclusion_tag("exercise/_points_progress.html")
def points_progress(points, max_points, passed=False, required=None):
    return _progress_data(points, max_points, passed, required)


@register.inclusion_tag("exercise/_points_progress.html")
def summary_progress(summary):
    return _progress_data(
        summary.get_total_points(),
        summary.get_max_points(),
        summary.is_passed(),
        summary.get_required_points())
