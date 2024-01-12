from django.template import loader


def group_info_context(group, profile):
    if not group:
        return { 'id': None }
    return {
        'id': group.id,
        'collaborators': group.collaborator_names(profile)
    }


def render_group_info(group, profile):
    template = loader.get_template("course/_group_info.html")
    return template.render(group_info_context(group, profile))
