from django.template import loader, Context

from lib.helpers import settings_text


def render_avatars(profiles):
    template = loader.get_template("course/_avatars.html")
    return template.render(Context({ 'profiles': profiles }))


def group_info_context(group, profile):
    if not group:
        return { 'id': None }
    return {
        'id': group.id,
        'collaborators': group.collaborator_names(profile),
        'avatars': render_avatars(group.members.all()),
    }


def render_group_info(group, profile):
    template = loader.get_template("course/_group_info.html")
    return template.render(Context(group_info_context(group, profile)))


def tags_context(profile, tags, instance):
    return {
        'user_id': profile.user.id,
        'external': profile.is_external,
        'internal_user_label': settings_text('INTERNAL_USER_LABEL'),
        'external_user_label': settings_text('EXTERNAL_USER_LABEL'),
        'tags': tags,
        'tag_ids': [tag.id for tag in tags],
        'course_id': instance.id,
    }


def render_tags(profile, tags, instance):
    template = loader.get_template("course/_tags.html")
    return template.render(Context(tags_context(profile, tags, instance)))

def render_usertag(tag):
    template = loader.get_template("course/_usertag.html")
    return template.render(Context({ 'tag': tag })).strip()
