from typing import Protocol, TYPE_CHECKING

from exercise.models import LearningObject, Submission
from lib.helpers import empty_at_runtime

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


@empty_at_runtime
class SupportsGetExerciseObject(Protocol):
    def get_exercise_object(self) -> LearningObject: ...


@empty_at_runtime
class SupportsGetSubmissionObject(Protocol):
    def get_submission_object(self) -> Submission: ...


@empty_at_runtime
class SupportsLearningObjects(Protocol):
    if TYPE_CHECKING:
        learning_objects: RelatedManager[LearningObject]
