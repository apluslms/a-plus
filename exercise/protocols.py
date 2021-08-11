from typing import Protocol, TYPE_CHECKING

from exercise.models import LearningObject, Submission
from lib.helpers import object_at_runtime

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


@object_at_runtime
class SupportsGetExerciseObject(Protocol):
    def get_exercise_object(self) -> LearningObject: ...


@object_at_runtime
class SupportsGetSubmissionObject(Protocol):
    def get_submission_object(self) -> Submission: ...


@object_at_runtime
class SupportsLearningObjects(Protocol):
    learning_objects: RelatedManager[LearningObject]
