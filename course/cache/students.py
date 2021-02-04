from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.urls import reverse

from lib.cache import CachedAbstract
from ..models import (
    USERTAG_EXTERNAL,
    USERTAG_INTERNAL,
    Enrollment,
    UserTag,
    UserTagging,
)
from userprofile.models import UserProfile


class CachedStudent(CachedAbstract):
    KEY_PREFIX = "student"

    def __init__(self, course_instance, userprofile):
        super().__init__(course_instance, userprofile)

    def _generate_data(self, course_instance, userprofile, *, data=None):
        if isinstance(userprofile, UserProfile):
            tags = (UserTagging.objects.get_all(userprofile, course_instance))
        else:
            tags = []
        return {
            'tag_slugs': [t.slug for t in tags],
        }


def invalidate_student(sender, instance: UserTagging, **kwargs):
    CachedStudent.invalidate(
        instance.course_instance,
        instance.user.user) # NOTE: userprofile.user

post_save.connect(invalidate_student, sender=UserTagging)
post_delete.connect(invalidate_student, sender=UserTagging)


def invalidate_students(sender, instance: UserTag, **kwargs):
    course = instance.course_instance
    for student in course.students.all():
        CachedStudent.invalidate(
            course,
            student.user)

post_save.connect(invalidate_students, sender=UserTag)
post_delete.connect(invalidate_students, sender=UserTag)
