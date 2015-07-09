from django import template

register = template.Library()


@register.filter
def course_module_classes(course_module):
    """
    Returns the CSS classes for the course module.
    """
    classes = []
    if course_module.is_open():
        classes.append("open")
    elif course_module.is_after_open():
        classes.append("closed")
        classes.append("collapsed")
    else:
        classes.append("upcoming")
        classes.append("collapsed")

    return " ".join(classes)


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
