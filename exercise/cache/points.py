import datetime
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Type, Tuple, Union

from django.contrib.auth.models import User
from django.db.models.base import Model
from django.db.models.aggregates import Max
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


def has_more_points(submission: Submission, current_entry: Dict[str, Any]) -> bool:
    if submission.grade == current_entry['points']:
        return is_newer(submission, current_entry)
    return submission.grade >= current_entry['points']


def is_newer(submission: Submission, current_entry: Dict[str, Any]) -> bool:
    return (
        current_entry['submission_date'] is None
        or submission.submission_time >= current_entry['submission_date']
    )


class CachedPoints(ContentMixin, CachedAbstract):
    KEY_PREFIX = 'points'

    @classmethod
    def invalidate(cls, course_instance: CourseInstance, user: User) -> None:
        # Invalidate both the staff cache and the non-staff cache
        super().invalidate(course_instance, user, modifiers=[str(False)])
        super().invalidate(course_instance, user, modifiers=[str(True)])

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
        self.is_staff = is_staff
        super().__init__(course_instance, user, modifiers=[str(is_staff)])

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
        exercise_revealed = {}

        # Augment submission parameters.
        def r_augment(children: List[Dict[str, Any]]) -> None:
            for entry in children:
                if entry['submittable']:
                    entry.update({
                        'submission_count': 0,
                        'submissions': [],
                        'best_submission': None,
                        'submission_date': None,
                        'points': 0,
                        'formatted_points': '0',
                        'passed': entry['points_to_pass'] == 0,
                        'graded': False,
                        'unofficial': False, # TODO: this should be True, but we need to ensure nothing breaks when it's changed
                        'forced_points': False,
                        'personal_deadline': None,
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

        if user.is_authenticated:
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
                            Q(submitter=user.userprofile)
                            | Q(exercise__submissions__submitters=user.userprofile)
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
            def r_reveal_feedback(children: List[Dict[str, Any]]) -> None:
                for entry in children:
                    if entry['submittable']:
                        exercise = BaseExercise.objects.get(id=entry['id'])
                        rule = exercise.active_submission_feedback_reveal_rule
                        state = ExerciseRevealState(entry)
                        is_revealed = rule.is_revealed(state)
                        reveal_time = rule.get_reveal_time(state)
                        entry['feedback_revealed'] = is_revealed
                        entry['feedback_reveal_time'] = reveal_time
                        exercise_revealed[exercise.id] = is_revealed, reveal_time
                        if (
                            reveal_time is not None
                            and reveal_time > timezone.now()
                            and (
                                data['invalidate_time'] is None
                                or reveal_time < data['invalidate_time']
                            )
                        ):
                            data['invalidate_time'] = reveal_time
                    r_reveal_feedback(entry.get('children', []))
            if not self.is_staff:
                for module in modules:
                    r_reveal_feedback(module['children'])

            # Augment submission data.
            submissions = (
                user.userprofile.submissions.exclude_errors()
                .filter(exercise__course_module__course_instance=instance)
                .prefetch_related('exercise')
                .only('id', 'exercise', 'submission_time', 'status', 'grade', 'force_exercise_points')
            )
            for submission in submissions:
                try:
                    tree = self._by_idx(modules, exercise_index[submission.exercise.id])
                except KeyError:
                    self.dirty = True
                    continue
                entry = tree[-1]
                if self.is_staff:
                    is_revealed = True
                    reveal_time = None
                else:
                    is_revealed, reveal_time = exercise_revealed[submission.exercise.id]
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
                    'points': submission.grade if is_revealed else 0,
                    'formatted_points': format_points(submission.grade, is_revealed, False),
                    'graded': submission.is_graded, # TODO: should this be official (is_graded = ready or unofficial)
                    'passed': (submission.grade >= entry['points_to_pass']) if is_revealed else False,
                    'submission_status': submission.status if not submission.is_graded else False,
                    'unofficial': unofficial,
                    'date': submission.submission_time,
                    'url': submission.get_url('submission-plain'),
                    'feedback_revealed': is_revealed,
                    'feedback_reveal_time': reveal_time,
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
                        'best_submission': submission.id,
                        'submission_date': submission.submission_time,
                        'points': submission.grade if is_revealed else 0,
                        'formatted_points': format_points(submission.grade, is_revealed, False),
                        'passed': (ready and submission.grade >= entry['points_to_pass']) if is_revealed else False,
                        'graded': True,
                        'unofficial': False,
                        'forced_points': True,
                    })
                if not entry.get('forced_points', False):
                    if (
                        ready and (
                            entry['unofficial'] or
                            is_better_than(submission, entry)
                        )
                    ) or (
                        unofficial and
                        not entry['graded'] and # NOTE: == entry['unofficial'], but before any submissions entry['unofficial'] is False
                        is_better_than(submission, entry)
                    ):
                        entry.update({
                            'best_submission': submission.id,
                            'submission_date': submission.submission_time,
                            'points': submission.grade if is_revealed else 0,
                            'formatted_points': format_points(submission.grade, is_revealed, False),
                            'passed': (ready and submission.grade >= entry['points_to_pass']) if is_revealed else False,
                            'graded': ready, # != unofficial
                            'unofficial': unofficial,
                        })
                if submission.notifications.count() > 0:
                    entry['notified'] = True
                    if submission.notifications.filter(seen=False).count() > 0:
                        entry['unseen'] = True

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

        data['points_created'] = timezone.now()
        return data

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
        CachedPoints.invalidate(course, profile)

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
