from django.core.cache import cache
from django.util import timezone

from exercise.models import Submission, BaseExercise
from .abstract import CachedAbstract
from .content import ContentMixin


class CachedPoints(ContentMixin, CachedAbstract):
    KEY_PREFIX = 'points'

    def __init__(self, course_instance, user, content):
        self.content = content
        self.instance = course_instance
        self.user = user
        super().__init__(course_instance, user)

    def _needs_generation(self, data):
        return data is None or data['created'] < self.content.created()

    def _generate_data(self, instance, user):
        data = self.content.data.copy()
        flat = data['flat']
        exercise_index = data['exercise_index']

        # Augment submission parameters.
        for entry in flat:
            entry.update({
                'submission_count': 0,
                'best_submission': None,
                'points': 0,
            })

        # Augment submission data.
        for submission in user.userprofile.submissions\
              .filter(exercise__course_module__course_instance=instance)\
              .exclude_errors():
            entry = flat[exercise_index[submission.exercise_id]]
            entry['submission_count'] += 1
            if submission.grade > entry['points']:
                entry.update({
                    'best_submission': submission.id,
                    'points': submission.grade,
                })

        # Collect hierarchial submission data.
        for entry in reversed(flat):
            if entry['type'] == 'exercise':
                parent = flat[entry['parent']]
                parent['max_points'] += entry['max_points']
                parent['submission_count'] += entry['submission_count']
                parent['points'] += entry['points']

        return data


def invalidate_content(sender, instance, **kwargs):
    course = instance.exercise.course_instance
    for profile in instance.submitters.all():
        CachedPoints.invalidate(course, profile.user)


# Automatically invalidate cached points when submissions change.
post_save.connect(invalidate_content, sender=Submission)
post_delete.connect(invalidate_content, sender=Submission)
