from datetime import timedelta
from django import template
from django.conf import settings
from django.utils import timezone
from django.utils.translation import get_language

from exercise.cache.content import CachedContent
from course.models import CourseInstance
from lib.localization_syntax import pick_localized
from ..cache.menu import CachedTopMenu
from ..renders import tags_context


register = template.Library()


def _prepare_topmenu(context):
    if 'topmenu' not in context:
        request = context.get('request', None)
        context['topmenu'] = CachedTopMenu(request.user if request else None)
    return context['topmenu']


@register.inclusion_tag("course/_course_dropdown_menu.html", takes_context=True)
def course_menu(context):
    menu = _prepare_topmenu(context)
    return { "instances": menu.courses() }


@register.inclusion_tag('course/_group_select.html', takes_context=True)
def group_select(context):
    instance = context.get('instance', None)
    if not instance:
        return { 'groups': [] }
    menu = _prepare_topmenu(context)
    groups, selected = menu.groups(instance)
    return {
        'instance': instance,
        'groups': groups,
        'selected': selected,
    }


@register.filter
def escape_slashes(string):
    return str(string).replace('/', '\/')

@register.filter
def parse_localization(entry):
    return pick_localized(entry, get_language())


@register.filter
def list_unselected(langs):
    listed = list(filter(lambda x: x and x != get_language(), langs.split("|")))
    return listed


@register.filter
def is_visible(entry):
    return CachedContent.is_visible(entry)


@register.filter
def is_listed(entry):
    return CachedContent.is_listed(entry)


@register.filter
def len_listed(entries):
    return len([e for e in entries if CachedContent.is_listed(e)])


@register.filter
def is_in_maintenance(entry):
    return CachedContent.is_in_maintenance(entry)


@register.filter
def is_open(entry, now):
    return entry['opening_time'] <= now <= entry['closing_time']


@register.filter
def has_opened(entry, now):
    return entry['opening_time'] <= now


@register.filter
def url(model_object, name=None):
    if name:
        return model_object.get_url(name)
    return model_object.get_display_url()


@register.filter
def names(profiles):
    return ", ".join(p.user.get_full_name() for p in profiles)


@register.inclusion_tag('course/_avatars.html')
def avatars(profiles):
    return { 'profiles': profiles }


@register.inclusion_tag("course/_profiles.html")
def profiles(profiles, instance, is_teacher):
    return {
        'instance': instance,
        'profiles': profiles,
        'is_teacher': is_teacher,
    }


@register.inclusion_tag("course/_tags.html")
def tags(profile, instance):
    # FIXME: get tags from cache
    return tags_context(profile, profile.taggings.tags_for_instance(instance), instance)


@register.filter
def enrollment_audience(enrollment_audience_val):
    # convert enrollment audience Enum value to the string description
    return CourseInstance.ENROLLMENT_AUDIENCE[enrollment_audience_val]


@register.filter
def view_content_to(view_content_to_val):
    # convert "view content to" Enum value to the string description
    return CourseInstance.VIEW_ACCESS[view_content_to_val]
