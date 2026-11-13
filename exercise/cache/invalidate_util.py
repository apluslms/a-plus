from __future__ import annotations
from typing import Any, Callable, Generator, Iterable, List, Optional, Tuple, Type, Union

from django.db.models import Model, Q

from course.models import CourseInstance, CourseModule
from deviations.models import SubmissionRuleDeviation
from notification.models import Notification
from threshold.models import CourseModuleRequirement, Threshold, ThresholdPoints
from userprofile.models import UserProfile
from ..models import BaseExercise, Submission, RevealRule, LearningObject, LearningObjectCategory


def modules_using_thresholds(threshold_ids: Iterable[int]) -> Generator[int, None, None]:
    yield from CourseModuleRequirement.objects.filter(
        threshold_id__in=threshold_ids
    ).values_list("module_id", flat=True).distinct()


def threshold_modules(threshold: Threshold) -> Generator[int, None, None]:
    yield from modules_using_thresholds([threshold.id])


def capture_previous_requirement_module( # pylint: disable=unused-argument
        sender: Type[CourseModuleRequirement],
        instance: CourseModuleRequirement,
        **kwargs: Any,
        ) -> None:
    if instance.pk is None:
        instance._previous_module_id = None
        return
    instance._previous_module_id = (
        CourseModuleRequirement.objects
        .filter(pk=instance.pk)
        .values_list("module_id", flat=True)
        .first()
    )


def requirement_modules(requirement: CourseModuleRequirement) -> Generator[int, None, None]:
    previous_module_id = getattr(requirement, "_previous_module_id", None)
    if previous_module_id is not None and previous_module_id != requirement.module_id:
        yield previous_module_id
    yield requirement.module_id


def capture_previous_threshold_point_owner( # pylint: disable=unused-argument
        sender: Type[ThresholdPoints],
        instance: ThresholdPoints,
        **kwargs: Any,
        ) -> None:
    if instance.pk is None:
        instance._previous_threshold_id = None
        return
    instance._previous_threshold_id = (
        ThresholdPoints.objects
        .filter(pk=instance.pk)
        .values_list("threshold_id", flat=True)
        .first()
    )


def threshold_point_modules(points: ThresholdPoints) -> Generator[int, None, None]:
    yield from modules_using_thresholds([points.threshold_id])


def saved_threshold_point_modules(points: ThresholdPoints) -> Generator[int, None, None]:
    threshold_ids = {points.threshold_id}
    previous_threshold_id = getattr(points, "_previous_threshold_id", None)
    if previous_threshold_id is not None:
        threshold_ids.add(previous_threshold_id)
    yield from modules_using_thresholds(threshold_ids)


def threshold_m2m_modules(
        instance: Union[CourseModule, LearningObjectCategory, BaseExercise, Threshold],
        action: str,
        pk_set: Optional[Iterable[int]],
        reverse: bool,
        ) -> Generator[int, None, None]:
    if action == "pre_clear" and reverse:
        instance._cleared_threshold_ids = list(
            getattr(instance, "threshold_set").values_list("id", flat=True)
        )
        return
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if reverse:
        if pk_set is None:
            threshold_ids = getattr(instance, "_cleared_threshold_ids", ())
        else:
            threshold_ids = pk_set
    else:
        threshold_ids = [instance.id]
    yield from modules_using_thresholds(threshold_ids)


def threshold_modules_for_target(
        target: Union[CourseModule, LearningObjectCategory, BaseExercise],
        ) -> Generator[int, None, None]:
    if isinstance(target, CourseModule):
        # Requirement text numbers the exercises of a passed module by the module's order
        threshold_ids = Threshold.objects.filter(
            Q(passed_modules=target) | Q(passed_exercises__course_module=target)
        ).values_list("id", flat=True)
    elif isinstance(target, LearningObjectCategory):
        threshold_ids = Threshold.objects.filter(passed_categories=target).values_list("id", flat=True)
    else:
        threshold_ids = Threshold.objects.filter(passed_exercises=target).values_list("id", flat=True)
    yield from modules_using_thresholds(threshold_ids)


def threshold_modules_for_learning_object(learning_object: LearningObject) -> Generator[int, None, None]:
    # Requirement text numbers an exercise by its chapters and module, so saving or deleting
    # a learning object can change the text of any passed exercise in the same module
    threshold_ids = Threshold.objects.filter(
        passed_exercises__course_module=learning_object.course_module_id
    ).values_list("id", flat=True)
    yield from modules_using_thresholds(threshold_ids)


def capture_previous_numbering( # pylint: disable=unused-argument
        sender: Type[CourseInstance],
        instance: CourseInstance,
        **kwargs: Any,
        ) -> None:
    instance._previous_numbering = (
        CourseInstance.objects
        .filter(pk=instance.pk)
        .values_list("content_numbering", "module_numbering")
        .first()
    )


def threshold_modules_for_numbering(instance: CourseInstance) -> Generator[int, None, None]:
    # Requirement text numbers passed modules and exercises, so only a numbering change can make it stale
    if getattr(instance, "_previous_numbering", None) == (instance.content_numbering, instance.module_numbering):
        return
    threshold_ids = Threshold.objects.filter(
        Q(passed_modules__course_instance=instance) | Q(passed_exercises__course_module__course_instance=instance)
    ).values_list("id", flat=True)
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
