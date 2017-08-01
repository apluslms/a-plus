from django.db.models.signals import post_save, post_delete

from lib.cached import CachedAbstract
from ..models import Enrollment
from ..renders import render_tags


class CachedStudents(CachedAbstract):
    KEY_PREFIX = "students"

    def __init__(self, course_instance):
        super().__init__(course_instance)

    def _generate_data(self, instance, data=None):
        participants = instance.students.all()\
            .prefetch_related('taggings')
        data = []
        for participant in participants:
            tags = [
                t.tag for t in participant.taggings.all()
                if t.course_instance == instance
            ]
            data.append({
                'id': participant.student_id or '',
                'last_name': participant.user.last_name or '',
                'first_name': participant.user.first_name or '',
                'email': participant.user.email or participant.user.username,
                'link': participant.get_url(instance),
                'tags': render_tags(participant, tags),
                'tag_ids': [t.id for t in tags],
                'external': participant.is_external,
            })
        return {
            'students': data,
        }

    def students(self):
        return self.data['students']


def invalidate_content(sender, instance, **kwargs):
    CachedStudents.invalidate(instance.course_instance)


post_save.connect(invalidate_content, sender=Enrollment)
post_delete.connect(invalidate_content, sender=Enrollment)
