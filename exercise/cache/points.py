from copy import deepcopy
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from lib.cached import CachedAbstract
from notification.models import Notification
from ..models import LearningObject, Submission
from .hierarchy import ContentMixin

class CachedPoints(ContentMixin, CachedAbstract):
    KEY_PREFIX = 'points'

    def __init__(self, course_instance, user, content):
        self.content = content
        self.instance = course_instance
        self.user = user
        super().__init__(course_instance, user)

    def _needs_generation(self, data):
        return data is None or data['created'] < self.content.created()

    def _generate_data(self, instance, user, data=None):
        data = deepcopy(self.content.data)
        module_index = data['module_index']
        exercise_index = data['exercise_index']
        modules = data['modules']
        categories = data['categories']
        total = data['total']

        # Augment submission parameters.
        def r_augment(children):
            for entry in children:
                if entry['submittable']:
                    entry.update({
                        'submission_count': 0,
                        'submissions': [],
                        'best_submission': None,
                        'points': 0,
                        'passed': entry['points_to_pass'] == 0,
                        'graded': False,
                    })
                r_augment(entry.get('children'))
        for module in modules:
            module.update({
                'submission_count': 0,
                'points': 0,
                'points_by_difficulty': {},
                'unconfirmed_points_by_difficulty': {},
                'passed': module['points_to_pass'] == 0,
            })
            r_augment(module['children'])
        for entry in categories.values():
            entry.update({
                'submission_count': 0,
                'points': 0,
                'points_by_difficulty': {},
                'unconfirmed_points_by_difficulty': {},
                'passed': entry['points_to_pass'] == 0,
            })
        total.update({
            'submission_count': 0,
            'points': 0,
            'points_by_difficulty': {},
            'unconfirmed_points_by_difficulty': {},
        })

        # Augment submission data.
        if user.is_authenticated():
            for submission in user.userprofile.submissions\
                  .exclude_errors()\
                  .filter(exercise__course_module__course_instance=instance):
                  #.prefetch_related("notifications"): breaks things
                try:
                    tree = self._by_idx(modules, exercise_index[submission.exercise.id])
                except KeyError:
                    self.dirty = True
                    continue
                entry = tree[-1]
                entry['submission_count'] += 1 if submission.status != Submission.STATUS.ERROR else 0
                entry['submissions'].append({
                    'id': submission.id,
                    'max_points': entry['max_points'],
                    'points_to_pass': entry['points_to_pass'],
                    'confirm_the_level': entry.get('confirm_the_level', False),
                    'submission_count': 1, # to fool points badge
                    'points': submission.grade,
                    'graded': submission.is_graded,
                    'passed': submission.grade >= entry['points_to_pass'],
                    'submission_status': submission.status if not submission.is_graded else False,
                    'unofficial': submission.status == Submission.STATUS.UNOFFICIAL,
                    'date': submission.submission_time,
                    'url': submission.get_url('submission-plain'),
                })
                if (
                    submission.status == Submission.STATUS.READY
                    and submission.grade >= entry['points']
                ):
                    entry.update({
                        'best_submission': submission.id,
                        'points': submission.grade,
                        'passed': submission.grade >= entry['points_to_pass'],
                        'graded': True,
                    })
                if submission.notifications.count() > 0:
                    entry['notified'] = True
                    if submission.notifications.filter(seen=False).count() > 0:
                        entry['unseen'] = True

        # Confirm points.
        def r_check(parent, children):
            for entry in children:
                if (
                    entry['submittable']
                    and entry['confirm_the_level']
                    and entry['passed']
                ):
                    if 'unconfirmed' in parent:
                        del(parent['unconfirmed'])
                    for child in parent.get('children', []):
                        if 'unconfirmed' in child:
                            del(child['unconfirmed'])
                r_check(entry, entry.get('children', []))
        for module in modules:
            r_check(module, module['children'])

        # Collect points and check limits.
        def add_to(target, entry):
            target['submission_count'] += entry['submission_count']
            if entry.get('unconfirmed', False):
                self._add_by_difficulty(
                    target['unconfirmed_points_by_difficulty'],
                    entry['difficulty'],
                    entry['points']
                )
            else:
                target['points'] += entry['points']
                self._add_by_difficulty(
                    target['points_by_difficulty'],
                    entry['difficulty'],
                    entry['points']
                )
        def r_collect(module, parent, children):
            passed = True
            max_points = 0
            submissions = 0
            points = 0
            confirm_entry = None
            for entry in children:
                if entry['submittable']:
                    if entry['confirm_the_level']:
                        confirm_entry = entry
                    else:
                        passed = passed and entry['passed']
                        max_points += entry['max_points']
                        submissions += entry['submission_count']
                        if entry['graded']:
                            points += entry['points']
                            add_to(module, entry)
                            add_to(categories[entry['category_id']], entry)
                            add_to(total, entry)
                passed = (
                    r_collect(module, entry, entry.get('children', []))
                    and passed
                )
            if confirm_entry and submissions > 0:
                confirm_entry['confirmable_points'] = True
            if parent and not parent['submittable']:
                parent['max_points'] = max_points
                parent['submission_count'] = submissions
                parent['points'] = points
            return passed
        for module in modules:
            passed = r_collect(module, None, module['children'])
            module['passed'] = (
                passed
                and module['points'] >= module['points_to_pass']
            )
        for category in categories.values():
            category['passed'] = (
                category['points'] >= category['points_to_pass']
            )

        data['points_created'] = timezone.now()
        return data

    def created(self):
        return self.data['points_created'], super().created()

    def submission_ids(self, category_id=None, module_id=None, exercise_id=None,
                       filter_for_assistant=False, best=True):
        exercises = self.search_exercises(
            category_id=category_id,
            module_id=module_id,
            exercise_id=exercise_id,
            filter_for_assistant=filter_for_assistant,
        )
        submissions = []
        if best:
            for entry in exercises:
                sid = entry.get('best_submission', None)
                if not sid is None:
                    submissions.append(sid)
        else:
            for entry in exercises:
                submissions.extend(s['id'] for s in entry.get('submissions', []))
        return submissions


def invalidate_content(sender, instance, **kwargs):
    course = instance.exercise.course_instance
    for profile in instance.submitters.all():
        CachedPoints.invalidate(course, profile.user)

def invalidate_notification(sender, instance, **kwargs):
    course = instance.course_instance
    if not course and instance.submission:
        course = instance.submission.exercise.course_instance
    CachedPoints.invalidate(course, instance.recipient.user)


# Automatically invalidate cached points when submissions change.
post_save.connect(invalidate_content, sender=Submission)
post_delete.connect(invalidate_content, sender=Submission)
post_save.connect(invalidate_notification, sender=Notification)
post_delete.connect(invalidate_notification, sender=Notification)
