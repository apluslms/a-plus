from __future__ import annotations
from typing import Callable, Generator, Iterable, List, Optional, Tuple, Union

from course.models import CourseModule
from deviations.models import SubmissionRuleDeviation
from notification.models import Notification
from userprofile.models import UserProfile
from ..models import BaseExercise, Submission, RevealRule, LearningObject, LearningObjectCategory


def learning_object_ancestors(lobj: LearningObject) -> Generator[int, None, None]:
    yield lobj.id
    lobj_index = {
        o.id: o
        for o in (
            LearningObject.bare_objects
            .filter(course_module=lobj.course_module)
            .only("id", "parent", "course_module")
        )
    }
    while lobj.parent_id is not None:
        parent = lobj_index.get(lobj.parent_id)
        if parent is None:
            # Parent was deleted at the same time, no need to invalidate it
            return
        lobj = parent
        yield lobj.id


def category_learning_objects(generator: Callable[[LearningObject], Generator[int, None, None]]):
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


def model_module_id(obj: RevealRule) -> Generator[int, None, None]:
    module = model_module(obj)
    if module is not None:
        yield module.id


def model_exercise_module_id(obj: ModelTypes):
    exercise = model_exercise(obj)
    if exercise is None:
        return
    yield exercise.course_module_id



def model_instance_id(obj: ModelTypes):
    if isinstance(obj, Notification) and obj.course_instance_id:
        instance_id = obj.course_instance_id
    else:
        exercise = model_exercise(obj)
        if exercise is None:
            return
        instance_id = exercise.course_module.course_instance_id

    yield instance_id


def model_exercise_ancestors(obj: ModelTypes) -> Generator[int, None, None]:
    exercise = model_exercise(obj)
    if exercise is None:
        return
    yield from learning_object_ancestors(exercise)


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
    if exercise is None:
        return
    yield from exercise_siblings_confirms_the_level(exercise)


def with_user_ids(
        generator: Callable[[ModelTypes], Generator[int, None, None]],
        ):
    def inner(obj: ModelTypes) -> Generator[Tuple[int, int], None, None]:
        user_ids = model_user_ids(obj)
        for model_id in generator(obj):
            for user_id in user_ids:
                yield (model_id, user_id)
    return inner


def m2m_submission_userprofile(generator: Callable[[Submission], Generator[int, None, None]]):
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
                for model_id in generator(submission):
                    if model_id in seen:
                        continue
                    seen.add(model_id)
                    yield (model_id, obj.id)
        else:
            for model_id in generator(obj):
                for user_id in pk_set:
                    yield (model_id, user_id)
                for user_id in model_user_ids(obj):
                    if user_id not in pk_set:
                        yield (model_id, user_id)
    return (inner, ["action", "pk_set"])
