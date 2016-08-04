from datetime import timedelta
from django import template
from django.conf import settings
from django.utils import timezone

from course.models import CourseInstance


register = template.Library()


@register.inclusion_tag("course/_course_dropdown_menu.html", takes_context=True)
def course_menu(context):
    if "course_menu" not in context:
        six_months_before = timezone.now() - timedelta(days=180)
        context["course_menu"] = \
            list(CourseInstance.objects.get_enrolled(context["user"], six_months_before)) + \
            list(CourseInstance.objects.get_on_staff(context["user"], six_months_before))
    return { "instances": context["course_menu"] }


@register.inclusion_tag('course/_group_select.html', takes_context=True)
def group_select(context):
    enrollment = None
    groups = []
    profile = context.get('profile', None)
    instance = context.get('instance', None)
    if profile and instance:
        enrollment = instance.get_enrollment_for(profile.user)
        groups = list(profile.groups.filter(course_instance=instance))

        # Annotate collaborators.
        def collaborators(group):
            return [p for p in group.members.all() if p != profile]
        if enrollment.selected_group:
            enrollment.selected_group.collaborators = collaborators(enrollment.selected_group)
        for g in groups:
            g.collaborators = collaborators(g)

    return {
        'enrollment': enrollment,
        'groups': groups,
        'profile': profile,
        'instance': instance,
    }


@register.filter
def url(model_object, name=None):
    if name:
        return model_object.get_url(name)
    return model_object.get_absolute_url()


@register.filter
def profiles(profiles):
    return ", ".join(
        "{} ({})".format(
            p.user.get_full_name(),
            p.student_id if p.student_id else p.user.username
        ) for p in profiles
    )


@register.filter
def names(profiles):
    return ", ".join(p.user.get_full_name() for p in profiles)


@register.inclusion_tag('course/_avatars.html')
def avatars(profiles):
    return { 'profiles': profiles }


@register.simple_tag
def brand_name():
    return settings.BRAND_NAME


@register.simple_tag
def site_alert():
    if settings.SITEWIDE_ALERT_TEXT:
        return '<div class="alert alert-danger">{}</div>'.format(
            settings.SITEWIDE_ALERT_TEXT)
    return ''
