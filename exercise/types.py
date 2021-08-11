from exercise.models import LearningObject, Submission
from lib.helpers import empty_at_runtime


@empty_at_runtime
class SupportsGetExerciseObject:
    def get_exercise_object(self) -> LearningObject: ...


@empty_at_runtime
class SupportsGetSubmissionObject:
    def get_submission_object(self) -> Submission: ...
