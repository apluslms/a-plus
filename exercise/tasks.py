import logging
from time import sleep

from aplus.celery import app
from .exercise_models import BaseExercise, ExerciseTask
from .submission_models import Submission

logger = logging.getLogger('aplus.exercise')

@app.task(bind=True)
def regrade_exercises(self, exerciseid: int, regrade_type: str) -> None:
    try:
        exercise = BaseExercise.objects.get(pk=exerciseid)
    except BaseExercise.DoesNotExist:
        logger.warning("regrade_exercises task: exercise id %s not found", exerciseid)
        return

    qs = (exercise.submissions
        .defer("feedback", "assistant_feedback", "grading_data")
    )

    if regrade_type == 'incomplete':
        qs = qs.filter(status__in=(
            Submission.STATUS.INITIALIZED,
            Submission.STATUS.WAITING,
            Submission.STATUS.ERROR
        ))

    count = 0
    total = qs.count()
    for submission in qs:
        page = exercise.grade(submission)
        for error in page.errors:
            logger.error( # pylint: disable=logging-fstring-interpolation
                f"regrade_exercises task error (Exercise: {exercise.id}, Submission: {submission.id}): {error}"
            )

        count += 1
        self.update_state(
            state='PROGRESS',
            meta={
                'current': count,
                'total': total,
            },
        )
        sleep(0.5)  # Delay 500 ms to avoid choking grader

    # Tell DB that there is no task running anymore
    try:
        task = ExerciseTask.objects.get(exercise=exercise, task_type=ExerciseTask.TASK_TYPE.REGRADE)
    except ExerciseTask.DoesNotExist:
        logger.warning(
            "regrade_exercises task: ExerciseTask %s has already been deleted before finishing",
            exercise.id)
        return
    task.delete()
