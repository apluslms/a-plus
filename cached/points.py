from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from exercise.models import Submission
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
        categories = data['categories']

        # Augment submission parameters.
        for entry in flat:
            entry.update({
                'submission_count': 0,
                'best_submission': None,
                'points': 0,
                'passed': True,
            })
            if entry['type'] == 'module':
                entry.update({
                    'max_points': 0,
                    'passed': True,
                })
        for entry in categories.values():
            entry.update({
                'max_points': 0,
                'submission_count': 0,
                'points': 0,
                'passed': True,
            })

        # Augment submission data.
        if user.is_authenticated:
            for submission in user.userprofile.submissions\
                  .exclude_errors()\
                  .filter(exercise__course_module__course_instance=instance):
                entry = flat[exercise_index[submission.exercise_id]]
                entry['submission_count'] += 1
                if submission.grade > entry['points']:
                    entry.update({
                        'best_submission': submission.id,
                        'points': submission.grade,
                    })

        # Collect hierarchial submission data.
        for index in exercise_index.values():
            entry = flat[index]
            category = categories[entry['category_id']]
            category['max_points'] += entry['max_points']
            category['submission_count'] += entry['submission_count']
            category['points'] += entry['points']
        for category in categories.values():
            category['passed'] = category['points'] >= category['points_to_pass']
        for entry in reversed(flat):
            if 'parent' in entry:
                parent = flat[entry['parent']]
                parent['max_points'] += entry['max_points']
                parent['submission_count'] += entry['submission_count']
                parent['points'] += entry['points']
            if entry['passed']:
                entry['passed'] = entry['points'] >= entry['points_to_pass']
            if 'parent' in entry:
                parent['passed'] = parent['passed'] and entry['passed']

        return data


def invalidate_content(sender, instance, **kwargs):
    course = instance.exercise.course_instance
    for profile in instance.submitters.all():
        CachedPoints.invalidate(course, profile.user)


# Automatically invalidate cached points when submissions change.
post_save.connect(invalidate_content, sender=Submission)
post_delete.connect(invalidate_content, sender=Submission)
