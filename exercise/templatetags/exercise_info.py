from django import template

register = template.Library()

@register.filter
def max_submissions(exercise, user_profile):
    return "{:d}/{:d}".format(
        exercise.get_submissions_for_student(user_profile).count(),
        exercise.max_submissions_for_student(user_profile)
    )

@register.filter
def percent(decimal):
    return int(decimal * 100)

@register.filter
def students(profiles):
    return ", ".join(
        profile.user.get_full_name() + \
            " ({})".format(profile.student_id) if profile.student_id else ""
        for profile in profiles
    )
