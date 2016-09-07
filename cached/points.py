from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from exercise.models import LearningObject, Submission
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
        total = data['total']

        # Augment submission parameters.
        for entry in flat:
            entry.update({
                'exercise_count': 0,
                'submission_count': 0,
                'best_submission': None,
                'points': 0,
                'points_by_difficulty': {},
                'passed': True,
            })
            if entry['type'] == 'module':
                entry.update({
                    'max_points': 0,
                    'difficulty': '',
                })
            elif entry['type'] == 'exercise':
                entry['graded'] = False
        for entry in categories.values():
            entry.update({
                'max_points': 0,
                'difficulty': 0,
                'exercise_count': 0,
                'submission_count': 0,
                'points': 0,
                'points_by_difficulty': {},
                'passed': True,
            })
        total.update({
            'exercise_count': 0,
            'max_points': 0,
            'difficulty': '',
            'submission_count': 0,
            'points': 0,
            'points_by_difficulty': {},
        })

        # Augment submission data.
        if user.is_authenticated():
            for submission in user.userprofile.submissions\
                  .exclude_errors()\
                  .filter(exercise__course_module__course_instance=instance):
                entry = flat[exercise_index[submission.exercise_id]]
                entry['submission_count'] += 1
                if (
                    submission.status == Submission.STATUS.READY
                    and submission.grade >= entry['points']
                ):
                    entry.update({
                        'best_submission': submission.id,
                        'graded': True,
                        'points': submission.grade,
                        'points_by_difficulty': {
                            entry['difficulty']: submission.grade,
                        },
                    })

        # Collect hierarchial submission data.
        def add_points_by_difficulty(src_entry, to_entry, subtract=False):
            src = src_entry['points_by_difficulty']
            to = to_entry['points_by_difficulty']
            for key in src:
                if key in to:
                    if subtract:
                        to[key] -= src[key]
                    else:
                        to[key] += src[key]
                else:
                    to[key] = 0 if subtract else src[key]
        for index in exercise_index.values():
            entry = flat[index]
            entry['exercise_count'] = 1
            category = categories[entry['category_id']]
            category['exercise_count'] += 1
            category['max_points'] += entry['max_points']
            category['submission_count'] += entry['submission_count']
            category['points'] += entry['points']
            add_points_by_difficulty(entry, category)
            total['exercise_count'] += 1
            total['max_points'] += entry['max_points']
            total['submission_count'] += entry['submission_count']
            total['points'] += entry['points']
            add_points_by_difficulty(entry, total)
        for entry in reversed(flat):
            parent = None
            if 'parent' in entry and entry['status'] != LearningObject.STATUS.HIDDEN:
                parent = flat[entry['parent']]
                parent['exercise_count'] += entry['exercise_count']
                parent['max_points'] += entry['max_points']
                parent['submission_count'] += entry['submission_count']
                parent['points'] += entry['points']
                add_points_by_difficulty(entry, parent)
            if entry['passed']:
                entry['passed'] = entry['points'] >= entry['points_to_pass']
            if parent:
                parent['passed'] = parent['passed'] and entry['passed']
                if entry['confirm_the_level']:
                    parent['unconfirmed'] = not entry['passed']
        for category in categories.values():
            category['passed'] = category['points'] >= category['points_to_pass']

        # Remove unconfirmed points.
        for entry in flat:
            if 'unconfirmed' in entry and entry['unconfirmed']:
                total['points'] -= entry['points']
                add_points_by_difficulty(entry, total, subtract=True)
        return data


def invalidate_content(sender, instance, **kwargs):
    course = instance.exercise.course_instance
    for profile in instance.submitters.all():
        CachedPoints.invalidate(course, profile.user)


# Automatically invalidate cached points when submissions change.
post_save.connect(invalidate_content, sender=Submission)
post_delete.connect(invalidate_content, sender=Submission)
