import itertools
from typing import Optional

from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max

from course.models import StudentGroup
from .cache.content import CachedContent
from .models import BaseExercise, Submission


class UserExerciseSummary:
    """
    UserExerciseSummary summarises the submissions of a certain user and
    exercise. It calculates some characterizing figures such as the number of
    submissions and reference to the best submission. See the public methods
    for more.
    """
    def __init__(self, exercise: BaseExercise, user: Optional[User] = None) -> None:
        self.exercise = exercise
        self.max_points = getattr(exercise, 'max_points', 0)
        self.difficulty = getattr(exercise, 'difficulty', '')
        self.points_to_pass = getattr(exercise, 'points_to_pass', 0)
        self.user = user
        self.submissions = []
        self.submission_count = 0
        self.best_submission = None
        self.graded = False
        self.unofficial = False
        self.forced_points = False

        if self.user and self.user.is_authenticated:
            self.submissions = list(
                exercise.get_submissions_for_student(user.userprofile)
                .select_related()
                # parent is prefetched because there may be multiple ancestors,
                # and they are needed for building the submission's URL.
                # submission_feedback_reveal_rule is prefetched because
                # nullable fields are not included in select_related().
                .prefetch_related('exercise__parent', 'exercise__submission_feedback_reveal_rule')
            )
            for s in self.submissions:
                if s.status not in (
                    Submission.STATUS.ERROR,
                    Submission.STATUS.REJECTED,
                ):
                    self.submission_count += 1

                    if s.force_exercise_points:
                        # This submission is chosen as the best submission and
                        # no further submissions are considered.
                        self.best_submission = s
                        self.unofficial = False
                        self.graded = True
                        self.forced_points = True
                    if not self.forced_points:
                        if (
                            s.status == Submission.STATUS.READY and (
                                self.best_submission is None
                                or self.unofficial
                                or self._is_better(s, self.best_submission)
                            )
                        ):
                            self.best_submission = s
                            self.unofficial = False
                            self.graded = True
                        elif (
                            s.status == Submission.STATUS.UNOFFICIAL and (
                                not self.graded
                                or (
                                    self.unofficial
                                    and self._is_better(s, self.best_submission)
                                )
                            )
                        ):
                            self.best_submission = s
                            self.unofficial = True

    def _is_better(self, submission1: Submission, submission2: Submission) -> bool:
        """
        Checks if `submission1` is better than `submission2`. This depends on
        the grading mode of the exercise.
        """
        if self.exercise.grading_mode == BaseExercise.GRADING_MODE.LAST:
            return submission1.submission_time > submission2.submission_time
        return (
            submission1.grade > submission2.grade
            or (
                submission1.grade == submission2.grade
                and submission1.submission_time > submission2.submission_time
            )
        )

    def get_submission_count(self):
        return self.submission_count

    def get_submissions(self):
        return self.submissions

    def get_best_submission(self):
        return self.best_submission

    def get_points(self):
        return self.best_submission.grade if self.best_submission and not self.unofficial else 0

    def get_penalty(self):
        return self.best_submission.late_penalty_applied if self.best_submission else None

    def is_missing_points(self):
        return self.get_points() < self.points_to_pass

    def is_full_points(self):
        return self.get_points() >= self.max_points

    def is_passed(self):
        return not self.is_missing_points()

    def is_submitted(self):
        return self.submission_count > 0

    def is_graded(self):
        return self.graded

    def is_unofficial(self):
        return self.unofficial

    def get_group(self) -> Optional[StudentGroup]:
        if self.submission_count > 0:
            s = self.submissions[0]
            if s.submitters.exists():
                return StudentGroup.get_exact(
                    self.exercise.course_instance,
                    s.submitters.all()
                )
        return None

    def get_group_id(self):
        group = self.get_group()
        return group.id if group else 0


class ResultTable:
    """
    WARNING: Constructing this class is a heavy database operation.

    Models the table displaying the grades for each student on each exercise.
    Result tables are generated dynamically when needed and not stored
    in a database.
    """

    def __init__(self, course_instance):
        """
        Instantiates a new ResultTable for the given course instance.
        After initialization the table is filled with grades from the database.
        """
        self.course_instance = course_instance

        # Exercises on the course.
        self.exercises = list(self.__get_exercises())
        self.categories = course_instance.categories.all()

        # Students on the course.
        self.students = list(course_instance.get_student_profiles())

        # Empty results table.
        self.results = {
            student.id: {
                exercise.id: None for exercise in self.exercises
            } for student in self.students
        }
        self.results_by_category = {
            student.id: {
                category.id: 0 for category in self.categories
            } for student in self.students
        }

        # Fill the results with the data from the database.
        self.__collect_student_grades()


    def __get_exercises(self):
        content = CachedContent(self.course_instance)

        def get_descendant_ids(node):
            children = node['children']
            if children:
                return itertools.chain.from_iterable(
                    get_descendant_ids(child) for child in children)
            return (node['id'],)

        root_node = { 'children': content.modules() }
        for id in get_descendant_ids(root_node): # pylint: disable=redefined-builtin
            try:
                yield BaseExercise.objects.get(learningobject_ptr_id=id)
            except ObjectDoesNotExist:
                continue


    def __collect_student_grades(self):
        """
        Helper for the __init__.
        This method puts the data from the database in to the results table.
        """
        submissions = list(Submission.objects \
            .filter(
                exercise__course_module__course_instance=self.course_instance,
                status=Submission.STATUS.READY
            ).values("submitters", "exercise", "exercise__category") \
            .annotate(best=Max("grade")) \
            .order_by()) # Remove default ordering.
        for submission in submissions:
            student_id = submission["submitters"]
            if student_id in self.results:
                self.results[student_id][submission["exercise"]] = submission["best"]
                self.results_by_category[student_id][submission["exercise__category"]] += submission["best"]


    def results_for_template(self):
        """
        Converts the results data into a form that is convenient for to use in a
        template. The columns of the table ordered according to the order of the
        exercises in self.exercises.
        """
        for_template = []
        for student in self.students:
            grades = [ self.results[student.id][exercise.id] \
                for exercise in self.exercises ]
            total = sum(g for g in grades if g is not None)
            for_template.append((student, grades, total))
        return for_template


    def max_sum(self):
        return sum(e.max_points for e in self.exercises)
