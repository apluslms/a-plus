from django.template import loader


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
