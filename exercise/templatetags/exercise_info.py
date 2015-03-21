from django import template

register = template.Library()

@register.filter
def max_submissions(exercise, user_profile):
    if exercise.max_submissions:
        return "%d/%d" % (exercise.get_submissions_for_student(
            user_profile).count(), exercise.max_submissions_for(user_profile))
    else:
        return "No restrictions"
