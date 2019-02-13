from copy import deepcopy
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.utils import timezone

from lib.cache import CachedAbstract
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
                        'unofficial': False,
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
            submissions = (
                user.userprofile.submissions.exclude_errors()
                .filter(exercise__course_module__course_instance=instance)
                .prefetch_related('exercise')
                .only('id', 'exercise', 'submission_time', 'status', 'grade')
            )
            for submission in submissions:
                try:
                    tree = self._by_idx(modules, exercise_index[submission.exercise.id])
                except KeyError:
                    self.dirty = True
                    continue
                entry = tree[-1]
                entry['submission_count'] += 1 if not submission.status in (Submission.STATUS.ERROR, Submission.STATUS.UNOFFICIAL) else 0
                unofficial = submission.status == Submission.STATUS.UNOFFICIAL
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
                    'unofficial': unofficial,
                    'date': submission.submission_time,
                    'url': submission.get_url('submission-plain'),
                })
                if (
                    submission.status == Submission.STATUS.READY and (
                        entry['unofficial']
                        or submission.grade >= entry['points']
                    )
                ) or (
                    unofficial and (
                        not entry['graded']
                        or (entry['unofficial'] and submission.grade > entry['points'])
                    )
                ):
                    entry.update({
                        'best_submission': submission.id,
                        'points': submission.grade,
                        'passed': not unofficial and submission.grade >= entry['points_to_pass'],
                        'graded': submission.status == Submission.STATUS.READY,
                        'unofficial': unofficial,
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
            if entry.get('unofficial', False):
                pass
            elif entry.get('unconfirmed', False):
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

    def submission_ids(self, number=None, category_id=None, module_id=None,
                       exercise_id=None, filter_for_assistant=False, best=True):
        exercises = self.search_exercises(
            number=number,
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

def invalidate_content_m2m(sender, instance, action, reverse, model, pk_set, **kwargs):
    # many-to-many field Submission.submitters may be modified without
    # triggering the Submission post save hook
    if action not in ('post_add', 'pre_remove'):
        return
    if reverse:
        # instance is a UserProfile
        if model == Submission:
            seen_courses = set()
            for submission_pk in pk_set:
                try:
                    submission = Submission.objects.get(pk=submission_pk)
                    course_instance = submission.exercise.course_instance
                    if course_instance.pk not in seen_courses:
                        CachedPoints.invalidate(course_instance, instance.user)
                    else:
                        seen_courses.add(course_instance.pk)
                except Submission.DoesNotExist:
                    pass
    else:
        # instance is a Submission
        invalidate_content(Submission, instance)

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
# listen to the m2m_changed signal since submission.submitters is a many-to-many
# field and instances must be saved before the many-to-many fields may be modified,
# that is to say, the submission post save hook may see an empty submitters list
m2m_changed.connect(invalidate_content_m2m, sender=Submission.submitters.through)
