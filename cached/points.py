from django.core.cache import cache
from django.util import timezone

from exercise.models import Submission
from .abstract import CachedAbstract
from .content import CachedContent


class CachedPoints(CachedAbstract):
    KEY_PREFIX = 'points'

    def __init__(self, course_instance, user):
        self.instance = course_instance
        self.user = user
        super().__init__(course_instance, user)

    def _generate_data(self, instance, user):
        exercise_summary = {}
        for submission in user.userprofile.submissions\
              .filter(exercise__course_module__course_instance=instance)\
              .exclude_errors():
            exercise = submission.exercise
            if not exercise.id in exercise_summary:
                exercise_summary[exercise.id] = {
                    'count': 1,
                    'grade': submission.grade,
                    'best': submission.id,
                }
            else:
                summary = exercise_summary[exercise_id]
                summary['count'] += 1
                if submission.grade > summary['grade']:
                    summary['grade'] = submission.grade
                    summary['best'] = submission.id
        return exercise_summary

    def exercise_summary(self, exercise):
        return self.data.get(exercise.id, {
            'count': 0,
            'grade': 0,
            'best': None,
        })


class CachedSummary(CachedAbstract):
    KEY_PREFIX = 'summary'

    def __init__(self, course_instance, user, content):
        self.instance = course_instance
        self.user = user
        self.content = content
        self.points = CachedPoints(course_instance, user)
        super().__init__(course_instance, user)

    def _needs_generation(self, data):
        return data is None and data['created'] > self.content.created()

    def _generate_data(self, instance, user):
        #TODO summarize points
        pass


def invalidate_content(sender, instance, **kwargs):
    course = instance.exercise.course_instance
    for profile in instance.submitters.all():
        CachedPoints.invalidate(course, profile.user)
        CachedSummary.invalidate(course, profile.user)


# Automatically invalidate cached points when submissions change.
post_save.connect(invalidate_content, sender=Submission)
post_delete.connect(invalidate_content, sender=Submission)
