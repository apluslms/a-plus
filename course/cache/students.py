from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.urls import reverse

from lib.cache import CachedAbstract
from ..models import (
    USERTAG_EXTERNAL,
    USERTAG_INTERNAL,
    Enrollment,
    UserTagging,
)


class CachedStudent(CachedAbstract):
    KEY_PREFIX = "student"

    def __init__(self, course_instance, user):
        super().__init__(course_instance, user)

    def _generate_data(self, course_instance, user, *, data=None):
        if isinstance(user, int):
            User = get_user_model()
            # required for is_external for external/internal tag
            user = User.objects.get(id=user)
        tags = (UserTagging.objects.get_all(user.userprofile, course_instance)
                if user else [])
        return {
            'tag_slugs': [t.slug for t in tags],
        }


def invalidate_student(sender, instance: UserTagging, **kwargs):
    CachedStudent.invalidate(
        instance.course_instance,
        instance.user.user) # NOTE: userprofile.user


post_save.connect(invalidate_student, sender=UserTagging)
post_delete.connect(invalidate_student, sender=UserTagging)
