from __future__ import annotations
from typing import Callable, Generator, Iterable, List, Optional, Tuple, Union

from django.db.models import Model

from course.models import CourseModule
from deviations.models import SubmissionRuleDeviation
from notification.models import Notification
from threshold.models import CourseModuleRequirement, Threshold, ThresholdPoints
from userprofile.models import UserProfile
from ..models import BaseExercise, Submission, RevealRule, LearningObject, LearningObjectCategory


def modules_using_thresholds(threshold_ids: Iterable[int]) -> Generator[int, None, None]:
    yield from CourseModuleRequirement.objects.filter(
        threshold_id__in=threshold_ids
    ).values_list("module_id", flat=True)


def threshold_modules(threshold: Threshold) -> Generator[int, None, None]:
    yield from modules_using_thresholds([threshold.id])


def previous_requirement_module(requirement: CourseModuleRequirement) -> Generator[int, None, None]:
    if requirement.pk is not None:
        module_id = CourseModuleRequirement.objects.filter(
            pk=requirement.pk
        ).values_list("module_id", flat=True).first()
        if module_id is not None and module_id != requirement.module_id:
            yield module_id


def previous_threshold_point_modules(points: ThresholdPoints) -> Generator[int, None, None]:
    if points.pk is not None:
        threshold_id = ThresholdPoints.objects.filter(
            pk=points.pk
        ).values_list("threshold_id", flat=True).first()
        if threshold_id is not None and threshold_id != points.threshold_id:
            yield from modules_using_thresholds([threshold_id])


def threshold_point_modules(points: ThresholdPoints) -> Generator[int, None, None]:
    yield from modules_using_thresholds([points.threshold_id])


def threshold_m2m_modules(
        instance: Union[CourseModule, LearningObjectCategory, BaseExercise, Threshold],
        pk_set: Optional[Iterable[int]],
        reverse: bool,
        ) -> Generator[int, None, None]:
    if reverse:
        if pk_set is None:
            threshold_ids = getattr(instance, "threshold_set").values_list("id", flat=True)
        else:
            threshold_ids = pk_set
    else:
        threshold_ids = [instance.id]
    yield from modules_using_thresholds(threshold_ids)


def threshold_modules_for_target(
        target: Union[CourseModule, LearningObjectCategory, BaseExercise],
        ) -> Generator[int, None, None]:
    if isinstance(target, CourseModule):
        threshold_ids = Threshold.objects.filter(passed_modules=target).values_list("id", flat=True)
    elif isinstance(target, LearningObjectCategory):
        threshold_ids = Threshold.objects.filter(passed_categories=target).values_list("id", flat=True)
    else:
        threshold_ids = Threshold.objects.filter(passed_exercises=target).values_list("id", flat=True)
    yield from modules_using_thresholds(threshold_ids)


def category_learning_objects(generator: Callable[[LearningObject], Iterable[int]]):
    def inner(category: LearningObjectCategory) -> Generator[int, None, None]:
        seen = set()
        for lobj in LearningObject.bare_objects.filter(category=category).only("id", "parent", "course_module"):
            for model_id in generator(lobj):
                if model_id in seen:
                    continue
                seen.add(model_id)
                yield model_id
    return inner


def module_learning_objects(module: CourseModule):
    for lobj in LearningObject.bare_objects.filter(course_module=module).only("id"):
        yield lobj.id


ModelTypes = Union[Submission, Notification, RevealRule, SubmissionRuleDeviation]
def model_user_ids(obj: ModelTypes) -> List[int]:
    if isinstance(obj, Submission):
        submitters = obj.submitters.all()
    elif isinstance(obj, Notification):
        submitters = [obj.recipient]
    elif isinstance(obj, RevealRule):
        exercise = model_exercise(obj)
        if exercise is not None:
            submitters = UserProfile.objects.filter(submissions__exercise=exercise).distinct()
        else:
            module = next(model_module(obj), None)
            if module is None:
                return []
            submitters = module.course_instance.get_student_profiles()
    else:
        submitters = UserProfile.objects.filter(
            submissions__exercise=obj.exercise,
            submissions__submitters=obj.submitter
        ).distinct()
        # We need to invalidate for the submitter even if they haven't submitted anything
        if not submitters:
            submitters = [obj.submitter]
    return [profile.user.id for profile in submitters]


def model_exercise(obj: ModelTypes) -> Optional[LearningObject]:
    if isinstance(obj, Notification):
        if obj.submission is None:
            return None
        exercise = obj.submission.exercise
    # pre_delete hook sets obj.exercise
    elif isinstance(obj, RevealRule) and not hasattr(obj, "exercise"):
        try:
            exercise = BaseExercise.objects.get(submission_feedback_reveal_rule=obj)
        except BaseExercise.DoesNotExist:
            return None
    else:
        exercise = obj.exercise
    return exercise


def model_module(obj: RevealRule) -> Generator[CourseModule, None, None]:
    if not hasattr(obj, "module"):
        try:
            module = CourseModule.objects.get(model_solution_reveal_rule=obj)
        except CourseModule.DoesNotExist:
            module = None
    else:
        module = obj.module

    if module is not None:
        yield module


def model_exercise_as_iterable(obj: ModelTypes) -> Generator[LearningObject, None, None]:
    exercise = model_exercise(obj)
    if exercise is not None:
        yield exercise


def exercise_siblings_confirms_the_level(exercise: LearningObject) -> Generator[int, None, None]:
    if exercise.parent is not None:
        for lobj in LearningObject.bare_objects.filter(parent=exercise.parent).only("id", "category"):
            if lobj.category.confirm_the_level:
                yield lobj.id
    else:
        for lobj in (
            LearningObject.bare_objects
            .filter(course_module=exercise.course_module, parent=None)
            .only("id", "category")
        ):
            if lobj.category.confirm_the_level:
                yield lobj.id


def model_exercise_siblings_confirms_the_level(obj: ModelTypes) -> Generator[int, None, None]:
    exercise = model_exercise(obj)
    if exercise is not None:
        yield from exercise_siblings_confirms_the_level(exercise)


def with_user_ids(
        generator: Callable[[ModelTypes], Generator[Union[int, Model], None, None]],
        ):
    def inner(obj: ModelTypes) -> Generator[Tuple[int, int], None, None]:
        user_ids = model_user_ids(obj)
        for model_id in generator(obj):
            if isinstance(model_id, Model):
                model_id = model_id.id
            for user_id in user_ids:
                yield (model_id, user_id)
    return inner


def m2m_submission_userprofile(generator: Callable[[Submission], Generator[LearningObject, None, None]]):
    def inner(
            obj: Union[Submission, UserProfile],
            action: str,
            pk_set: Iterable[int],
            ) -> Generator[Tuple[int, int], None, None]:
        if action not in ('post_add', 'pre_remove'):
            return
        if isinstance(obj, UserProfile):
            submissions = Submission.objects.filter(pk__in=pk_set)
            seen = set()
            for submission in submissions:
                for model in generator(submission):
                    if model.id in seen:
                        continue
                    seen.add(model.id)
                    yield (model.id, obj.id)
        else:
            for model in generator(obj):
                for user_id in pk_set:
                    yield (model.id, user_id)
                for user_id in model_user_ids(obj):
                    if user_id not in pk_set:
                        yield (model.id, user_id)
    return (inner, ["action", "pk_set"])
