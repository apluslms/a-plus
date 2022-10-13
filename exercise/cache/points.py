import datetime
from copy import deepcopy
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Type,
    Tuple,
    Union,
)

from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.db.models.base import Model
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


def has_more_points(submission: Submission, current_best_submission: Optional[Submission]) -> bool:
    if current_best_submission is None:
        return True
    if submission.grade == current_best_submission.grade:
        return is_newer(submission, current_best_submission)
    return submission.grade >= current_best_submission.grade


def is_newer(submission: Submission, current_best_submission: Optional[Submission]) -> bool:
    return (
        current_best_submission is None
        or submission.submission_time >= current_best_submission.submission_time
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
        self._extract_tuples(self.data, 0 if is_staff else 1)

    def _needs_generation(self, data: Dict[str, Any]) -> bool:
        return (
            data is None
            or data['created'] < self.content.created()
            or (
                data.get('invalidate_time') is not None
                and timezone.now() >= data['invalidate_time']
            )
        )

    def _generate_data( # pylint: disable=arguments-differ
            self,
            instance: CourseInstance,
            user: User,
            data: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
        # Perform all database queries before generating the cache.
        if user.is_authenticated:
            submissions = list(
                user.userprofile.submissions.exclude_errors()
                .filter(exercise__course_module__course_instance=instance)
                .select_related()
                .prefetch_related('exercise__parent', 'exercise__submission_feedback_reveal_rule', 'notifications')
                .only('id', 'exercise', 'submission_time', 'status', 'grade', 'force_exercise_points')
                .order_by('exercise', '-submission_time')
            )
            exercises = BaseExercise.objects.filter(course_module__course_instance=instance)
            deadline_deviations = list(
                DeadlineRuleDeviation.objects
                .get_max_deviations(user.userprofile, exercises)
            )
            submission_deviations = list(
                MaxSubmissionsRuleDeviation.objects
                .get_max_deviations(user.userprofile, exercises)
            )
        else:
            submissions = []
            deadline_deviations = []
            submission_deviations = []

        # Generate the staff and student version of the cache, and merge them.
        generate_args = (user.is_authenticated, submissions, deadline_deviations, submission_deviations)
        staff_data = self._generate_data_internal(True, *generate_args)
        student_data = self._generate_data_internal(False, *generate_args)
        self._pack_tuples(staff_data, student_data) # Now staff_data is the final, combined data.

        # Pick the lowest invalidate_time if it is duplicated.
        invalidate_time = staff_data['invalidate_time']
        if isinstance(invalidate_time, tuple):
            if invalidate_time[0] is not None:
                if invalidate_time[1] is not None:
                    staff_data['invalidate_time'] = min(invalidate_time)
                else:
                    staff_data['invalidate_time'] = invalidate_time[0]
            else:
                staff_data['invalidate_time'] = invalidate_time[1]

        staff_data['points_created'] = timezone.now()
        return staff_data

    def _generate_data_internal( # noqa: MC0001
            self,
            is_staff: bool,
            is_authenticated: bool,
            submissions: Iterable[Submission],
            deadline_deviations: Iterable[DeadlineRuleDeviation],
            submission_deviations: Iterable[MaxSubmissionsRuleDeviation],
            ) -> Dict[str, Any]:
        """
        Handles the generation of one version of the cache (staff or student).
        All source data is prefetched by `_generate_data` and provided as
        arguments to this method.
        """
        data = deepcopy(self.content.data)
        module_index = data['module_index'] # noqa: F841
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
                        'best_submission': None,
                        'points': 0,
                        'formatted_points': '0',
                        'passed': entry['points_to_pass'] == 0,
                        'graded': False,
                        'unofficial': False, # TODO: this should be True,
                        # but we need to ensure nothing breaks when it's changed
                        'forced_points': False,
                        'personal_deadline': None,
                        'personal_deadline_has_penalty': None,
                        'personal_max_submissions': None,
                        'feedback_revealed': True,
                        'feedback_reveal_time': None,
                    })
                r_augment(entry.get('children'))
        for module in modules:
            module.update({
                'submission_count': 0,
                'points': 0,
                'formatted_points': '0',
                'points_by_difficulty': {},
                'unconfirmed_points_by_difficulty': {},
                'passed': module['points_to_pass'] == 0,
                'feedback_revealed': True,
            })
            r_augment(module['children'])
        for entry in categories.values():
            entry.update({
                'submission_count': 0,
                'points': 0,
                'formatted_points': '0',
                'points_by_difficulty': {},
                'unconfirmed_points_by_difficulty': {},
                'passed': entry['points_to_pass'] == 0,
                'feedback_revealed': True,
            })
        total.update({
            'submission_count': 0,
            'points': 0,
            'points_by_difficulty': {},
            'unconfirmed_points_by_difficulty': {},
        })

        if is_authenticated:
            # Augment deviation data.
            for deviation in deadline_deviations:
                try:
                    tree = self._by_idx(modules, exercise_index[deviation.exercise.id])
                except KeyError:
                    self.dirty = True
                    continue
                entry = tree[-1]
                entry['personal_deadline'] = (
                    entry['closing_time'] + datetime.timedelta(minutes=deviation.extra_minutes)
                )
                entry['personal_deadline_has_penalty'] = not deviation.without_late_penalty

            for deviation in submission_deviations:
                try:
                    tree = self._by_idx(modules, exercise_index[deviation.exercise.id])
                except KeyError:
                    self.dirty = True
                    continue
                entry = tree[-1]
                entry['personal_max_submissions'] = (
                    entry['max_submissions'] + deviation.extra_submissions
                )

            # Initialize variables for the submission loop.
            exercise = None
            entry = None
            is_better_than = None
            final_submission = None
            last_submission = None

            def check_reveal_rule() -> None:
                """
                Evaluate the reveal rule of the current exercise and ensure
                that feedback is hidden appropriately.
                """
                rule = exercise.active_submission_feedback_reveal_rule
                state = ExerciseRevealState(entry)
                is_revealed = rule.is_revealed(state)
                reveal_time = rule.get_reveal_time(state)

                entry.update({
                    'best_submission': entry['best_submission'] if is_revealed else last_submission.id,
                    'points': entry['points'] if is_revealed else 0,
                    'formatted_points': format_points(entry['points'], is_revealed, False),
                    'passed': entry['passed'] if is_revealed else False,
                    'feedback_revealed': is_revealed,
                    'feedback_reveal_time': reveal_time,
                })

                for submission in entry['submissions']:
                    submission.update({
                        'points': submission['points'] if is_revealed else 0,
                        'formatted_points': format_points(submission['points'], is_revealed, False),
                        'passed': submission['passed'] if is_revealed else False,
                        'feedback_revealed': is_revealed,
                        'feedback_reveal_time': reveal_time,
                    })

                # If the reveal rule depends on time, update the cache's
                # invalidation time.
                if (
                    reveal_time is not None
                    and reveal_time > timezone.now()
                    and (
                        data['invalidate_time'] is None
                        or reveal_time < data['invalidate_time']
                    )
                ):
                    data['invalidate_time'] = reveal_time

            # Augment submission data.
            for submission in submissions:
                # The submissions are ordered by exercise. Check here if the
                # exercise has changed.
                if exercise is None or submission.exercise.id != exercise.id:
                    if exercise is not None and not is_staff:
                        # Check the reveal rule of the last exercise now that
                        # all of its submissions have been iterated.
                        check_reveal_rule()
                    final_submission = None
                    last_submission = None
                    # These variables stay constant throughout the exercise.
                    exercise = submission.exercise
                    try:
                        tree = self._by_idx(modules, exercise_index[exercise.id])
                    except KeyError:
                        self.dirty = True
                        continue
                    entry = tree[-1]
                    if exercise.grading_mode == BaseExercise.GRADING_MODE.BEST:
                        is_better_than = has_more_points
                    elif exercise.grading_mode == BaseExercise.GRADING_MODE.LAST:
                        is_better_than = is_newer
                    else:
                        is_better_than = has_more_points
                ready = submission.status == Submission.STATUS.READY
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
                    'points': submission.grade,
                    'formatted_points': format_points(submission.grade, True, False),
                    'graded': submission.is_graded, # TODO: should this be official (is_graded = ready or unofficial)
                    'passed': (submission.grade >= entry['points_to_pass']),
                    'submission_status': submission.status if not submission.is_graded else False,
                    'unofficial': unofficial,
                    'date': submission.submission_time,
                    'url': submission.get_url('submission-plain'),
                    'feedback_revealed': True,
                    'feedback_reveal_time': None,
                })
                # Update best submission if exercise points are not forced, and
                # one of these is true:
                # 1) current submission in ready (thus is not unofficial) AND
                #    a) current best is an unofficial OR
                #    b) current submission is better depending on grading mode
                # 2) All of:
                #    - current submission is unofficial AND
                #    - current best is unofficial
                #    - current submission is better depending on grading mode
                if submission.force_exercise_points:
                    # This submission is chosen as the final submission and no
                    # further submissions are considered.
                    entry.update({
                        'best_submission': submission.id,
                        'points': submission.grade,
                        'formatted_points': format_points(submission.grade, True, False),
                        'passed': (ready and submission.grade >= entry['points_to_pass']),
                        'graded': True,
                        'unofficial': False,
                        'forced_points': True,
                    })
                    final_submission = submission
                if not entry.get('forced_points', False):
                    if ( # pylint: disable=too-many-boolean-expressions
                        ready and (
                            entry['unofficial'] or
                            is_better_than(submission, final_submission)
                        )
                    ) or (
                        unofficial and
                        not entry['graded'] and # NOTE: == entry['unofficial'],
                        # but before any submissions entry['unofficial'] is False
                        is_better_than(submission, final_submission)
                    ):
                        entry.update({
                            'best_submission': submission.id,
                            'points': submission.grade,
                            'formatted_points': format_points(submission.grade, True, False),
                            'passed': (ready and submission.grade >= entry['points_to_pass']),
                            'graded': ready, # != unofficial
                            'unofficial': unofficial,
                        })
                        final_submission = submission
                # Update last_submission to be the last submission, or the last
                # official submission if there are any official submissions.
                # Note that the submissions are ordered by descendng time.
                if last_submission is None or (
                    last_submission.status == Submission.STATUS.UNOFFICIAL
                    and not unofficial
                ):
                    last_submission = submission
                if submission.notifications.exists():
                    entry['notified'] = True
                    if submission.notifications.filter(seen=False).exists():
                        entry['unseen'] = True
            # All submissions of all exercises have been iterated. Check the
            # reveal rule of the last exercise (if there was one).
            if exercise is not None and not is_staff:
                check_reveal_rule()

        # Confirm points.
        def r_check(parent: Dict[str, Any], children: List[Dict[str, Any]]) -> None:
            for entry in children:
                if (
                    entry['submittable']
                    and entry['confirm_the_level']
                    and entry['passed']
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
            target['feedback_revealed'] = target.get('feedback_revealed', False) and entry['feedback_revealed']
            # NOTE: entry can be only ready or unofficial (exercise level
            # points are only copied, only if submission is in ready or
            # unofficial state)
            if entry.get('unofficial', False):
                pass
            # thus, all points are now ready..
            elif entry.get('unconfirmed', False):
                self._add_by_difficulty(
                    target['unconfirmed_points_by_difficulty'],
                    entry['difficulty'],
                    entry['points']
                )
            # and finally, only remaining points are official (not unofficial & not unconfirmed)
            else:
                target['points'] += entry['points']
                target['formatted_points'] = format_points(
                    target['points'],
                    target['feedback_revealed'],
                    True,
                )
                self._add_by_difficulty(
                    target['points_by_difficulty'],
                    entry['difficulty'],
                    entry['points']
                )

        def r_collect(
                module: Dict[str, Any],
                parent: Dict[str, Any],
                children: List[Dict[str, Any]],
                ) -> Tuple[bool, bool]:
            passed = True
            is_revealed = True
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
                        is_revealed = is_revealed and entry['feedback_revealed']
                        max_points += entry['max_points']
                        submissions += entry['submission_count']
                        if entry['graded']:
                            points += entry['points']
                            add_to(module, entry)
                            add_to(categories[entry['category_id']], entry)
                            add_to(total, entry)
                r_passed, r_is_revealed = r_collect(module, entry, entry.get('children', []))
                passed = r_passed and passed
                is_revealed = r_is_revealed and is_revealed
            if confirm_entry and submissions > 0:
                confirm_entry['confirmable_points'] = True
            if parent and not parent['submittable']:
                parent['max_points'] = max_points
                parent['submission_count'] = submissions
                parent['points'] = points
                parent['formatted_points'] = format_points(points, is_revealed, True)
            return passed, is_revealed
        for module in modules:
            passed, _ = r_collect(module, None, module['children'])
            module['passed'] = (
                passed
                and module['points'] >= module['points_to_pass']
            )
        for category in categories.values():
            category['passed'] = (
                category['points'] >= category['points_to_pass']
            )

        return data

    def created(self) -> Tuple[datetime.datetime, datetime.datetime]:
        return self.data['points_created'], super().created()

    def submission_ids( # pylint: disable=too-many-arguments
            self,
            number: Optional[str] = None,
            category_id: Optional[int] = None,
            module_id: Optional[int] = None,
            exercise_id: Optional[int] = None,
            filter_for_assistant: bool = False,
            best: bool = True,
            fallback_to_last: bool = False,
            raise_404=True,
            ) -> List[int]:
        exercises = self.search_exercises(
            number=number,
            category_id=category_id,
            module_id=module_id,
            exercise_id=exercise_id,
            filter_for_assistant=filter_for_assistant,
            raise_404=raise_404,
        )
        submissions = []
        if best:
            for entry in exercises:
                sid = entry.get('best_submission', None)
                if sid is not None:
                    submissions.append(sid)
                elif fallback_to_last:
                    entry_submissions = entry.get('submissions', [])
                    if entry_submissions:
                        submissions.append(entry_submissions[0]['id']) # Last submission is first in the cache
        else:
            for entry in exercises:
                submissions.extend(s['id'] for s in entry.get('submissions', []))
        return submissions

    def _pack_tuples(self, value1, value2, parent_container=None, parent_key=None):
        """
        Compare two data structures, and when conflicting values are found,
        pack them into a tuple. `value1` is modified in this operation.

        Example: when called with `value1={"key1": "a", "key2": "b"}` and
        `value2={"key1": "a", "key2": "c"}`, `value1` will become
        `{"key1": "a", "key2": ("b", "c")}`.
        """
        if isinstance(value1, dict):
            for key, inner_value1 in value1.items():
                inner_value2 = value2[key]
                self._pack_tuples(inner_value1, inner_value2, value1, key)
        elif isinstance(value1, list):
            for index, inner_value1 in enumerate(value1):
                inner_value2 = value2[index]
                self._pack_tuples(inner_value1, inner_value2, value1, index)
        else:
            if value1 != value2:
                parent_container[parent_key] = (value1, value2)

    def _extract_tuples(self, value, tuple_index, parent_container=None, parent_key=None):
        """
        Find tuples within a data structure, and replace them with the value
        at `tuple_index` in the tuple. `value` is modified in this operation.

        Example: when called with `value={"key1": "a", "key2": ("b", "c")}` and
        `tuple_index=0`, `value` will become `{"key1": "a", "key2": "b"}`.
        """
        if isinstance(value, dict):
            for key, inner_value in value.items():
                self._extract_tuples(inner_value, tuple_index, value, key)
        elif isinstance(value, list):
            for index, inner_value in enumerate(value):
                self._extract_tuples(inner_value, tuple_index, value, index)
        elif isinstance(value, tuple):
            parent_container[parent_key] = value[tuple_index]

# pylint: disable-next=unused-argument
def invalidate_content(sender: Type[Model], instance: Submission, **kwargs: Any) -> None:
    course = instance.exercise.course_instance
    for profile in instance.submitters.all():
        CachedPoints.invalidate(course, profile.user)

def invalidate_content_m2m( # pylint: disable=too-many-arguments
        sender: Type[Model], # pylint: disable=unused-argument
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
# pylint: disable-next=unused-argument
def invalidate_notification(sender: Type[Model], instance: Notification, **kwargs: Any) -> None:
    course = instance.course_instance
    if not course and instance.submission:
        course = instance.submission.exercise.course_instance
    CachedPoints.invalidate(course, instance.recipient.user)
# pylint: disable-next=unused-argument
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
# pylint: disable-next=unused-argument
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
