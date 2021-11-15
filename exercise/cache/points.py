import datetime
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Type, Tuple, Union

from django.contrib.auth.models import User
from django.db.models.base import Model
from django.db.models.aggregates import Max
from django.db.models.expressions import Exists, OuterRef
from django.db.models.query_utils import Q
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.utils import timezone

from course.models import CourseInstance
from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation, SubmissionRuleDeviation
from lib.cache import CachedAbstract
from lib.helpers import format_points
from notification.models import Notification
from userprofile.models import UserProfile
from ..models import BaseExercise, Submission, RevealRule
from ..reveal_states import ExerciseRevealState
from .content import CachedContent
from .hierarchy import ContentMixin


def has_more_points(submission: Submission, current_entry: Dict[str, Any], is_staff: bool) -> bool:
    key = '_staff_points' if is_staff else '_student_points'
    if submission.grade == current_entry[key]:
        return is_newer(submission, current_entry, is_staff)
    return submission.grade >= current_entry[key]


def is_newer(submission: Submission, current_entry: Dict[str, Any], is_staff: bool) -> bool:
    key = '_staff_best_submission_date' if is_staff else '_student_best_submission_date'
    return (
        current_entry[key] is None
        or submission.submission_time >= current_entry[key]
    )


class CachedPoints(ContentMixin, CachedAbstract):
    """
    Extends `CachedContent` to include data about a user's submissions and
    points in the course's exercises.

    Note that the `data` returned by this is dependent on the `is_staff`
    parameter. When `is_staff` is `False`, reveal rules are respected and
    exercise results are hidden when the reveal rule does not evaluate to true.
    When `is_staff` is `True`, reveal rules are ignored and the results are
    always revealed.
    """
    KEY_PREFIX = 'points'

    # Store a mapping of keys that are prefixed, so the unprefix method doesn't
    # have to parse each key and can instead compare them to this mapping.
    prefixed_keys = {}
    for key in [
        'best_submission',
        'best_submission_date',
        'points',
        'formatted_points',
        'passed',
        'feedback_revealed',
        'feedback_reveal_time',
        'points_by_difficulty',
        'unconfirmed_points_by_difficulty',
    ]:
        prefixed_keys['_staff_' + key] = (True, key)
        prefixed_keys['_student_' + key] = (False, key)

    def __init__(
            self,
            course_instance: CourseInstance,
            user: User,
            content: CachedContent,
            is_staff: bool = False,
            ) -> None:
        self.content = content
        self.instance = course_instance
        self.user = user
        super().__init__(course_instance, user)
        self._unprefix(self.data, is_staff)

    def _needs_generation(self, data: Dict[str, Any]) -> bool:
        return (
            data is None
            or data['created'] < self.content.created()
            or (
                data.get('invalidate_time') is not None
                and timezone.now() >= data['invalidate_time']
            )
        )

    def _generate_data(
            self,
            instance: CourseInstance,
            user: User,
            data: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
        data = deepcopy(self.content.data)
        module_index = data['module_index']
        exercise_index = data['exercise_index']
        modules = data['modules']
        categories = data['categories']
        total = data['total']
        data['invalidate_time'] = None

        # Augment submission parameters.
        def r_augment(children: List[Dict[str, Any]]) -> None:
            for entry in children:
                if entry['submittable']:
                    entry.update({
                        'submission_count': 0,
                        'submissions': [],
                        'graded': False,
                        'unofficial': False, # TODO: this should be True, but we need to ensure nothing breaks when it's changed
                        'forced_points': False,
                        'personal_deadline': None,
                        'personal_max_submissions': None,
                        '_staff_best_submission': None,
                        '_staff_best_submission_date': None,
                        '_staff_points': 0,
                        '_staff_formatted_points': format_points(0, True, False),
                        '_staff_passed': entry['points_to_pass'] == 0,
                        '_staff_feedback_revealed': True,
                        '_staff_feedback_reveal_time': None,
                        # Exercises are displayed as unrevealed until reveal rules are evaluated
                        '_student_best_submission': None,
                        '_student_best_submission_date': None,
                        '_student_points': 0,
                        '_student_formatted_points': format_points(0, False, False),
                        '_student_passed': entry['points_to_pass'] == 0,
                        '_student_feedback_revealed': False,
                        '_student_feedback_reveal_time': None,
                    })
                r_augment(entry.get('children'))
        for module in modules:
            module.update({
                'submission_count': 0,
                '_staff_points': 0,
                '_staff_formatted_points': format_points(0, True, True),
                '_staff_points_by_difficulty': {},
                '_staff_unconfirmed_points_by_difficulty': {},
                '_staff_passed': module['points_to_pass'] == 0,
                '_staff_feedback_revealed': True,
                '_student_points': 0,
                '_student_formatted_points': format_points(0, True, True),
                '_student_points_by_difficulty': {},
                '_student_unconfirmed_points_by_difficulty': {},
                '_student_passed': module['points_to_pass'] == 0,
                '_student_feedback_revealed': False,
            })
            r_augment(module['children'])
        for entry in categories.values():
            entry.update({
                'submission_count': 0,
                '_staff_points': 0,
                '_staff_formatted_points': format_points(0, True, True),
                '_staff_points_by_difficulty': {},
                '_staff_unconfirmed_points_by_difficulty': {},
                '_staff_passed': entry['points_to_pass'] == 0,
                '_staff_feedback_revealed': True,
                '_student_points': 0,
                '_student_formatted_points': format_points(0, True, True),
                '_student_points_by_difficulty': {},
                '_student_unconfirmed_points_by_difficulty': {},
                '_student_passed': entry['points_to_pass'] == 0,
                '_student_feedback_revealed': False,
            })
        total.update({
            'submission_count': 0,
            '_staff_points': 0,
            '_staff_points_by_difficulty': {},
            '_staff_unconfirmed_points_by_difficulty': {},
            '_student_points': 0,
            '_student_points_by_difficulty': {},
            '_student_unconfirmed_points_by_difficulty': {},
        })

        if user.is_authenticated:
            # Augment submission data.
            submissions = (
                user.userprofile.submissions.exclude_errors()
                .filter(exercise__course_module__course_instance=instance)
                .prefetch_related('exercise', 'notifications')
                .only('id', 'exercise', 'submission_time', 'status', 'grade', 'force_exercise_points')
            )
            for submission in submissions:
                try:
                    tree = self._by_idx(modules, exercise_index[submission.exercise.id])
                except KeyError:
                    self.dirty = True
                    continue
                entry = tree[-1]
                ready = submission.status == Submission.STATUS.READY
                staff_passed = submission.grade >= entry['points_to_pass']
                staff_formatted_points = format_points(submission.grade, True, False)
                unofficial = submission.status == Submission.STATUS.UNOFFICIAL
                if ready or submission.status in (Submission.STATUS.WAITING, Submission.STATUS.INITIALIZED):
                    entry['submission_count'] += 1
                entry['submissions'].append({
                    'type': 'submission',
                    'id': submission.id,
                    'max_points': entry['max_points'],
                    'points_to_pass': entry['points_to_pass'],
                    'confirm_the_level': entry.get('confirm_the_level', False),
                    'submission_count': 1, # to fool points badge
                    'graded': submission.is_graded, # TODO: should this be official (is_graded = ready or unofficial)
                    'submission_status': submission.status if not submission.is_graded else False,
                    'unofficial': unofficial,
                    'date': submission.submission_time,
                    'url': submission.get_url('submission-plain'),
                    '_staff_points': submission.grade,
                    '_staff_formatted_points': staff_formatted_points,
                    '_staff_passed': staff_passed,
                    '_staff_feedback_revealed': True,
                    '_staff_feedback_reveal_time': None,
                    # Submissions are displayed as unrevealed until reveal rules are evaluated
                    '_student_points': 0,
                    '_student_formatted_points': format_points(0, False, False),
                    '_student_passed': entry['points_to_pass'] == 0,
                    '_student_feedback_revealed': False,
                    '_student_feedback_reveal_time': None,
                })
                # TODO: implement way to select algorithm for the best
                if submission.exercise.grading_mode == BaseExercise.GRADING_MODE.BEST:
                    is_better_than = has_more_points
                elif submission.exercise.grading_mode == BaseExercise.GRADING_MODE.LAST:
                    is_better_than = is_newer
                else:
                    is_better_than = has_more_points
                # Update best submission if one of these is true
                # 1) current submission in ready (thus is not unofficial) AND
                #    a) current best is an unofficial OR
                #    b) current submission has better grade
                # 2) All of:
                #    - current submission is unofficial AND
                #    - current best is unofficial
                #    - current submission has better grade
                if submission.force_exercise_points:
                    # This submission is chosen as the best submission and no
                    # further submissions are considered.
                    entry.update({
                        'graded': True,
                        'unofficial': False,
                        'forced_points': True,
                        '_staff_best_submission': submission.id,
                        '_staff_best_submission_date': submission.submission_time,
                        '_staff_points': submission.grade,
                        '_staff_formatted_points': staff_formatted_points,
                        '_staff_passed': staff_passed,
                    })
                if not entry.get('forced_points', False):
                    if (
                        ready and (
                            entry['unofficial'] or
                            is_better_than(submission, entry, True)
                        )
                    ) or (
                        unofficial and
                        not entry['graded'] and # NOTE: == entry['unofficial'], but before any submissions entry['unofficial'] is False
                        is_better_than(submission, entry, True)
                    ):
                        entry.update({
                            'graded': ready, # != unofficial
                            'unofficial': unofficial,
                            '_staff_best_submission': submission.id,
                            '_staff_best_submission_date': submission.submission_time,
                            '_staff_points': submission.grade,
                            '_staff_formatted_points': staff_formatted_points,
                            '_staff_passed': staff_passed,
                        })

                # For student data, the best submission is the last one that is
                # not unofficial.
                if (
                    ready and (
                        entry['unofficial'] or
                        is_newer(submission, entry, False)
                    )
                ) or (
                    unofficial and
                    not entry['graded'] and
                    is_newer(submission, entry, False)
                ):
                    entry.update({
                        '_student_best_submission': submission.id,
                        '_student_best_submission_date': submission.submission_time,
                    })

                if submission.notifications.count() > 0:
                    entry['notified'] = True
                    if submission.notifications.filter(seen=False).count() > 0:
                        entry['unseen'] = True

            # Augment deviation data.
            def get_max_deviations(
                    cls: Type[SubmissionRuleDeviation],
                    field: str,
                    ) -> Iterable[Tuple[Dict[str, Any], int]]:
                # This function gets the maximum deviation of the given type
                # for the current user, and returns the corresponding cache
                # item as well as the deviation value.
                results = (
                    cls.objects.filter(
                        Q(exercise__course_module__course_instance=instance)
                        & (
                            # Check that the owner of the deviation is the
                            # current user, OR it belongs to some other
                            # user who has submitted the deviation's exercise
                            # WITH the current user.
                            Q(submitter=user.userprofile)
                            | Exists(
                                # Note the two 'submitters' filters.
                                Submission.objects.filter(
                                    exercise=OuterRef('exercise'),
                                    submitters=OuterRef('submitter'),
                                ).filter(
                                    submitters=user.userprofile,
                                )
                            )
                        )
                    )
                    .values('exercise')
                    .annotate(max_deviation=Max(field))
                )

                for result in results:
                    try:
                        tree = self._by_idx(modules, exercise_index[result['exercise']])
                    except KeyError:
                        self.dirty = True
                        continue
                    entry = tree[-1]
                    yield entry, result['max_deviation']

            for entry, extra_minutes in (
                get_max_deviations(DeadlineRuleDeviation, 'extra_minutes')
            ):
                entry['personal_deadline'] = (
                    entry['closing_time'] + datetime.timedelta(minutes=extra_minutes)
                )

            for entry, extra_submissions in (
                get_max_deviations(MaxSubmissionsRuleDeviation, 'extra_submissions')
            ):
                entry['personal_max_submissions'] = (
                    entry['max_submissions'] + extra_submissions
                )

            # Augment exercise reveal rules.
            for exercise in (
                BaseExercise.objects
                .filter(course_module__course_instance=instance)
                .prefetch_related('submission_feedback_reveal_rule')
                .only('id', 'submission_feedback_reveal_rule')
            ):
                try:
                    tree = self._by_idx(modules, exercise_index[exercise.id])
                except KeyError:
                    self.dirty = True
                    continue
                entry = tree[-1]
                rule = exercise.active_submission_feedback_reveal_rule

                # Evaluate the reveal rule using the real (staff) values.
                entry_copy = dict(entry)
                del entry_copy['submissions'] # Not needed by the reveal rule and we don't want to unprefix them.
                self._unprefix(entry_copy, True)
                state = ExerciseRevealState(entry_copy)
                is_revealed = rule.is_revealed(state)
                reveal_time = rule.get_reveal_time(state)

                entry.update({
                    '_student_feedback_revealed': is_revealed,
                    '_student_feedback_reveal_time': reveal_time,
                })
                if is_revealed:
                    entry.update({
                        '_student_best_submission': entry['_staff_best_submission'],
                        '_student_points': entry['_staff_points'],
                        '_student_formatted_points': entry['_staff_formatted_points'],
                        '_student_passed': entry['_staff_passed'],
                    })

                for submission in entry['submissions']:
                    submission.update({
                        '_student_feedback_revealed': is_revealed,
                        '_student_feedback_reveal_time': reveal_time,
                    })
                    if is_revealed:
                        submission.update({
                            '_student_points': submission['_staff_points'],
                            '_student_formatted_points': submission['_staff_formatted_points'],
                            '_student_passed': submission['_staff_passed'],
                        })

                if (
                    reveal_time is not None
                    and reveal_time > timezone.now()
                    and (
                        data['invalidate_time'] is None
                        or reveal_time < data['invalidate_time']
                    )
                ):
                    data['invalidate_time'] = reveal_time

        # Confirm points.
        def r_check(parent: Dict[str, Any], children: List[Dict[str, Any]]) -> None:
            for entry in children:
                if (
                    entry['submittable']
                    and entry['confirm_the_level']
                    and entry['_staff_passed'] # Delayed feedback is not considered here
                ):
                    parent.pop('unconfirmed', None)
                    for child in parent.get('children', []):
                        child.pop('unconfirmed', None)
                        # TODO: should recurse to all descendants
                r_check(entry, entry.get('children', []))
        for module in modules:
            r_check(module, module['children'])

        # Collect points and check limits.
        def add_to(target: Dict[str, Any], entry: Dict[str, Any]) -> None:
            target['submission_count'] += entry['submission_count']
            target['_staff_feedback_revealed'] = (
                target.get('_staff_feedback_revealed', False)
                and entry['_staff_feedback_revealed']
            )
            target['_student_feedback_revealed'] = (
                target.get('_student_feedback_revealed', False)
                and entry['_student_feedback_revealed']
            )
            # NOTE: entry can be only ready or unofficial (exercise level
            # points are only copied, only if submission is in ready or
            # unofficial state)
            if entry.get('unofficial', False):
                pass
            # thus, all points are now ready..
            elif entry.get('unconfirmed', False):
                self._add_by_difficulty(
                    target['_staff_unconfirmed_points_by_difficulty'],
                    entry['difficulty'],
                    entry['_staff_points']
                )
                self._add_by_difficulty(
                    target['_student_unconfirmed_points_by_difficulty'],
                    entry['difficulty'],
                    entry['_student_points']
                )
            # and finally, only remaining points are official (not unofficial & not unconfirmed)
            else:
                target['_staff_points'] += entry['_staff_points']
                target['_student_points'] += entry['_student_points']
                target['_staff_formatted_points'] = format_points(
                    target['_staff_points'],
                    target['_staff_feedback_revealed'],
                    True,
                )
                target['_student_formatted_points'] = format_points(
                    target['_student_points'],
                    target['_student_feedback_revealed'],
                    True,
                )
                self._add_by_difficulty(
                    target['_staff_points_by_difficulty'],
                    entry['difficulty'],
                    entry['_staff_points']
                )
                self._add_by_difficulty(
                    target['_student_points_by_difficulty'],
                    entry['difficulty'],
                    entry['_student_points']
                )
        def r_collect(
                module: Dict[str, Any],
                parent: Dict[str, Any],
                children: List[Dict[str, Any]],
                ) -> Tuple[bool, bool, bool, bool]:
            staff_passed = True
            student_passed = True
            staff_is_revealed = True
            student_is_revealed = True
            max_points = 0
            submissions = 0
            staff_points = 0
            student_points = 0
            confirm_entry = None
            for entry in children:
                if entry['submittable']:
                    if entry['confirm_the_level']:
                        confirm_entry = entry
                    else:
                        staff_passed = staff_passed and entry['_staff_passed']
                        student_passed = student_passed and entry['_student_passed']
                        staff_is_revealed = staff_is_revealed and entry['_staff_feedback_revealed']
                        student_is_revealed = student_is_revealed and entry['_student_feedback_revealed']
                        max_points += entry['max_points']
                        submissions += entry['submission_count']
                        if entry['graded']:
                            staff_points += entry['_staff_points']
                            student_points += entry['_student_points']
                            add_to(module, entry)
                            add_to(categories[entry['category_id']], entry)
                            add_to(total, entry)
                staff_r_passed, staff_r_is_revealed, student_r_passed, student_r_is_revealed = (
                    r_collect(module, entry, entry.get('children', []))
                )
                staff_passed = staff_r_passed and staff_passed
                student_passed = student_r_passed and student_passed
                staff_is_revealed = staff_r_is_revealed and staff_is_revealed
                student_is_revealed = student_r_is_revealed and student_is_revealed
            if confirm_entry and submissions > 0:
                confirm_entry['confirmable_points'] = True
            if parent and not parent['submittable']:
                parent['max_points'] = max_points
                parent['submission_count'] = submissions
                parent['_staff_points'] = staff_points
                parent['_student_points'] = student_points
                parent['_staff_formatted_points'] = format_points(staff_points, staff_is_revealed, True)
                parent['_student_formatted_points'] = format_points(student_points, student_is_revealed, True)
            return staff_passed, staff_is_revealed, student_passed, student_is_revealed
        for module in modules:
            staff_passed, _, student_passed, _ = r_collect(module, None, module['children'])
            module['_staff_passed'] = (
                staff_passed
                and module['_staff_points'] >= module['points_to_pass']
            )
            module['_student_passed'] = (
                student_passed
                and module['_student_points'] >= module['points_to_pass']
            )
        for category in categories.values():
            category['_staff_passed'] = (
                category['_staff_points'] >= category['points_to_pass']
            )
            category['_student_passed'] = (
                category['_student_points'] >= category['points_to_pass']
            )

        data['points_created'] = timezone.now()
        return data

    def _unprefix(self, data: Dict[str, Any], is_staff: bool) -> None:
        """
        Traverses the input dict recursively and removes the prefixed keys,
        keeping only the staff values or student values depending on the
        `is_staff` parameter.

        E.g. `{"_staff_points": 10, "_student_points": 0}` becomes
        `{"points": 10}` when `is_staff` is `True`.
        """
        prefixed_keys = CachedPoints.prefixed_keys
        for key, value in list(data.items()):
            if isinstance(value, dict):
                self._unprefix(value, is_staff)
            elif isinstance(value, list):
                self._unprefix_list(value, is_staff)
            if isinstance(key, str):
                if key in prefixed_keys:
                    del data[key]
                    is_staff_key, unprefixed_key = prefixed_keys[key]
                    if is_staff_key == is_staff:
                        data[unprefixed_key] = value

    def _unprefix_list(self, data: List[Any], is_staff: bool) -> None:
        """
        Traverses the input list recursively and calls calls `_unprefix` for
        the dicts within the list.
        """
        for item in data:
            if isinstance(item, dict):
                self._unprefix(item, is_staff)
            elif isinstance(item, list):
                self._unprefix_list(item, is_staff)

    def created(self) -> Tuple[datetime.datetime, datetime.datetime]:
        return self.data['points_created'], super().created()

    def submission_ids(
            self,
            number: Optional[str] = None,
            category_id: Optional[int] = None,
            module_id: Optional[int] = None,
            exercise_id: Optional[int] = None,
            filter_for_assistant: bool = False,
            best: bool = True,
            ) -> List[int]:
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


def invalidate_content(sender: Type[Model], instance: Submission, **kwargs: Any) -> None:
    course = instance.exercise.course_instance
    for profile in instance.submitters.all():
        CachedPoints.invalidate(course, profile.user)

def invalidate_content_m2m(
        sender: Type[Model],
        instance: Union[Submission, UserProfile],
        action: str,
        reverse: bool,
        model: Type[Model],
        pk_set: Iterable[int],
        **kwargs: Any,
        ) -> None:
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

def invalidate_notification(sender: Type[Model], instance: Notification, **kwargs: Any) -> None:
    course = instance.course_instance
    if not course and instance.submission:
        course = instance.submission.exercise.course_instance
    CachedPoints.invalidate(course, instance.recipient.user)

def invalidate_deviation(sender: Type[Model], instance: SubmissionRuleDeviation, **kwargs: Any) -> None:
    # Invalidate for the student who received the deviation as well as all
    # students who have submitted this exercise with them.
    course = instance.exercise.course_instance
    CachedPoints.invalidate(course, instance.submitter.user)
    submitters = UserProfile.objects.filter(
        submissions__exercise=instance.exercise,
        submissions__submitters=instance.submitter
    ).distinct()
    for profile in submitters:
        if profile != instance.submitter:
            CachedPoints.invalidate(course, profile.user)

def invalidate_submission_reveal(sender: Type[Model], instance: RevealRule, **kwargs: Any) -> None:
    # Invalidate for all students who have submitted the exercise whose
    # submission feedback reveal rule changed.
    try:
        exercise = BaseExercise.objects.get(submission_feedback_reveal_rule=instance)
    except BaseExercise.DoesNotExist:
        return
    course = exercise.course_instance
    submitters = UserProfile.objects.filter(submissions__exercise=exercise).distinct()
    for profile in submitters:
        CachedPoints.invalidate(course, profile.user)

# Automatically invalidate cached points when submissions change.
post_save.connect(invalidate_content, sender=Submission)
post_delete.connect(invalidate_content, sender=Submission)
post_save.connect(invalidate_notification, sender=Notification)
post_delete.connect(invalidate_notification, sender=Notification)
post_save.connect(invalidate_deviation, sender=DeadlineRuleDeviation)
post_delete.connect(invalidate_deviation, sender=DeadlineRuleDeviation)
post_save.connect(invalidate_deviation, sender=MaxSubmissionsRuleDeviation)
post_delete.connect(invalidate_deviation, sender=MaxSubmissionsRuleDeviation)
post_save.connect(invalidate_submission_reveal, sender=RevealRule)
post_delete.connect(invalidate_submission_reveal, sender=RevealRule)
# listen to the m2m_changed signal since submission.submitters is a many-to-many
# field and instances must be saved before the many-to-many fields may be modified,
# that is to say, the submission post save hook may see an empty submitters list
m2m_changed.connect(invalidate_content_m2m, sender=Submission.submitters.through)
