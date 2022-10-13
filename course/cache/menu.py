from django.db.models.signals import post_save, post_delete, m2m_changed

from lib.cache import CachedAbstract
from ..models import StudentGroup, Enrollment, CourseInstance
from ..renders import render_group_info


class CachedTopMenu(CachedAbstract):
    KEY_PREFIX = 'topmenu'

    def __init__(self, user):
        self.user = user
        super().__init__(user)

    def _generate_data(self, user, data=None): # pylint: disable=arguments-differ
        profile = user.userprofile if user and user.is_authenticated else None
        return {
            'courses': self._generate_courses(profile),
            'groups': self._generate_groups(profile),
        }

    def _generate_courses(self, profile):
        if not profile:
            return []

        def course_entry(instance):
            return {
                'name': str(instance),
                'link': instance.get_absolute_url(),
            }

        def divider_entry():
            return {
                'divider': True,
            }

        enrolled = []
        for instance in CourseInstance.objects.get_enrolled(profile).all():
            if instance.visible_to_students:
                enrolled.append(course_entry(instance))

        teaching = []
        for instance in CourseInstance.objects.get_teaching(profile).all():
            teaching.append(course_entry(instance))

        assisting = []
        for instance in CourseInstance.objects.get_assisting(profile).all():
            assisting.append(course_entry(instance))

        courses = []
        courses.extend(enrolled)
        if courses and teaching:
            courses.append(divider_entry())
        courses.extend(teaching)
        if courses and assisting:
            courses.append(divider_entry())
        courses.extend(assisting)
        return courses

    def _generate_groups(self, profile):
        if not profile:
            return {}

        def group_entry(group):
            return {
                'id': group.id,
                'size': group.members.count(),
                'collaborators': group.collaborator_names(profile),
            }

        group_map = {}
        for enrollment in Enrollment.objects\
                .filter(user_profile=profile,
                    status=Enrollment.ENROLLMENT_STATUS.ACTIVE)\
                .select_related('selected_group')\
                .prefetch_related('selected_group__members'):
            instance_id = enrollment.course_instance_id
            group_map[instance_id] = (
                [
                    group_entry(g) for g in (
                        profile.groups
                        .filter(course_instance_id=instance_id)
                        .prefetch_related('members')
                    )
                ],
                render_group_info(enrollment.selected_group, profile)
            )
        return group_map

    def courses(self):
        return self.data['courses']

    def groups(self, instance):
        return self.data['groups'].get(instance.id, ([],None))


def invalidate_content(sender, instance, **kwargs): # pylint: disable=unused-argument
    CachedTopMenu.invalidate(instance.user_profile.user)

def invalidate_assistants(sender, instance, reverse=False, **kwargs): # pylint: disable=unused-argument
    if reverse:
        CachedTopMenu.invalidate(instance.user)
    else:
        for profile in instance.assistants.all():
            CachedTopMenu.invalidate(profile.user)

def invalidate_teachers(sender, instance, reverse=False, **kwargs): # pylint: disable=unused-argument
    if reverse:
        CachedTopMenu.invalidate(instance.user)
    else:
        for profile in instance.teachers.all():
            CachedTopMenu.invalidate(profile.user)

def invalidate_members(sender, instance, reverse=False, **kwargs): # pylint: disable=unused-argument
    if reverse:
        CachedTopMenu.invalidate(instance.user)
    else:
        for profile in instance.members.all():
            CachedTopMenu.invalidate(profile.user)


# Automatically invalidate cached menu when enrolled or edited.
post_save.connect(invalidate_content, sender=Enrollment)
post_delete.connect(invalidate_content, sender=Enrollment)
m2m_changed.connect(invalidate_assistants, sender=Enrollment)
m2m_changed.connect(invalidate_teachers, sender=Enrollment)
m2m_changed.connect(invalidate_members, sender=StudentGroup.members.through)
