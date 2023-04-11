from django.db.models.signals import post_save, post_delete

from lib.cache import CachedAbstract
from .models import MenuItem


class CachedCourseMenu(CachedAbstract):
    KEY_PREFIX = 'coursemenu'

    def __init__(self, course_instance):
        self.instance = course_instance
        super().__init__(course_instance)

    def _generate_data(self, instance, data=None): # pylint: disable=arguments-differ
        student_groups = {}
        student_order = []
        staff_groups = {}
        staff_order = []

        def append_to_group(groups, group_order, group_label, menu_entry):
            if group_label not in group_order:
                group_order.append(group_label)
                groups[group_label] = {
                    'label': group_label,
                    'items': [],
                }
            groups[group_label]['items'].append(menu_entry)

        for menu in instance.ext_services.all():
            url = menu.url
            entry = {
                'enabled': menu.is_enabled,
                'access': menu.access,
                'label': menu.label,
                'icon_class': menu.icon_class,
                'url': url,
                'blank': bool(menu.service),
            }
            group = menu.menu_group_label or ""

            if menu.access > MenuItem.ACCESS.STUDENT:
                append_to_group(staff_groups, staff_order, group, entry)
            else:
                append_to_group(student_groups, student_order, group, entry)

        return {
            'student_groups': [student_groups[g] for g in student_order],
            'staff_groups': [staff_groups[g] for g in staff_order],
        }

    def student_link_groups(self):
        return self.data['student_groups']

    def staff_link_groups(self):
        return self.data['staff_groups']

    @classmethod
    def is_assistant_link(cls, entry):
        return entry['access'] <= MenuItem.ACCESS.ASSISTANT


def invalidate_content(sender, instance, **kwargs): # pylint: disable=unused-argument
    CachedCourseMenu.invalidate(instance.course_instance)


# Automatically invalidate cached menu when edited.
post_save.connect(invalidate_content, sender=MenuItem)
post_delete.connect(invalidate_content, sender=MenuItem)
