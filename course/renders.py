from django.template import loader

from lib.helpers import settings_text


def render_avatars(profiles):
    template = loader.get_template("course/_avatars.html")
    return template.render({ 'profiles': profiles })


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
    return template.render(group_info_context(group, profile))


def tags_context(profile, tags, instance):
    return {
        'user_id': profile.user_id,
        'external': profile.is_external,
        'internal_user_label': settings_text('INTERNAL_USER_LABEL'),
        'external_user_label': settings_text('EXTERNAL_USER_LABEL'),
        'tags': tags,
        'tag_ids': [tag.id for tag in tags],
        'instance': instance,
    }


def render_tags(profile, tags, instance):
    template = loader.get_template("course/_tags.html")
    return template.render(tags_context(profile, tags, instance))
