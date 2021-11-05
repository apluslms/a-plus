import logging
from time import sleep

from celery import current_task
from django.db.models import Q
from aplus.celery import app
from .exercise_models import BaseExercise

logger = logging.getLogger('aplus.exercise')

@app.task
def regrade_exercises(exerciseid: int, uri_prefix: str, regrade_type: str) -> None:
    exercise = BaseExercise.objects.get(pk=exerciseid)

    qs = exercise.submissions\
        .defer("feedback", "submission_data", "grading_data")

    if regrade_type == 'incomplete':
        qs = qs.filter(Q(status='INITIALIZED') | Q(status='WAITING') | Q(status='ERROR'))

    total = qs.count()

    # FIXME: "Simulated" type is used for testing with arbitrarily higher loads.
    # It will be removed from the final PR, along with the "iterations" variable.
    iterations = 1
    if regrade_type == 'simulated':
        iterations = 15
        total = total * iterations

    count = 0
    while iterations > 0:
        for i in qs:
            # The grade method would like to see HttpRequest, but we don't have one.
            # Instead, we have URI prefix from recent request that is enough for
            # composing the address for grader.
            page = exercise.grade(None, i, uri_prefix)
            for error in page.errors:
                logger.error(f"Mass regrade error: {error}")

            current_task.update_state(
                 state='PROGRESS',
                 meta={
                     'current': count,
                     'total': total,
                 },
             )
            count = count + 1
            sleep(0.5)  # Delay 500 ms to avoid choking grader

        iterations = iterations - 1

    # Tell DB that there is no task running anymore
    exercise.regrade_task = ''
    exercise.save()
