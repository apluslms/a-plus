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
from deviations.models import MaxSubmissionsRuleDeviation, DeadlineRuleDeviation
from course.models import CourseModule

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
        dl_deviations = (DeadlineRuleDeviation.objects.filter(
                submitter=user.userprofile,
                exercise__course_module__course_instance=course_instance
            ) if user else [])
        bonus_submissions = (MaxSubmissionsRuleDeviation.objects.filter(
                submitter=user.userprofile,
                exercise__course_module__course_instance=course_instance
            ) if user else [])
        return {
            'tag_slugs': [t.slug for t in tags],
            'dl_deviations': {
                d.exercise.id: (d.get_new_deadline(), d.without_late_penalty) for d in dl_deviations},
            'submission_deviations': {
                d.exercise.id: d.extra_submissions for d in bonus_submissions},
        }


def invalidate_student(sender, instance, **kwargs):
    if hasattr(instance, 'user'):
        CachedStudent.invalidate(
            instance.course_instance,
            instance.user.user) # NOTE: userprofile.user
    else:
        CachedStudent.invalidate(
            instance.exercise.course_module.course_instance,
            instance.submitter.user) # NOTE: userprofile.user

post_save.connect(invalidate_student, sender=UserTagging)
post_delete.connect(invalidate_student, sender=UserTagging)
post_save.connect(invalidate_student, sender=DeadlineRuleDeviation)
post_delete.connect(invalidate_student, sender=DeadlineRuleDeviation)
post_save.connect(invalidate_student, sender=MaxSubmissionsRuleDeviation)
post_delete.connect(invalidate_student, sender=MaxSubmissionsRuleDeviation)


def invalidate_students(sender, instance: UserTag, **kwargs):
    course = instance.course_instance
    for student in course.students.all():
        CachedStudent.invalidate(
            course,
            student.user)

post_save.connect(invalidate_students, sender=UserTag)
post_delete.connect(invalidate_students, sender=UserTag)
