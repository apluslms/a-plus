from django.db.models import Max

from course.models import StudentGroup
from .models import BaseExercise, Submission


class UserExerciseSummary(object):
    """
    UserExerciseSummary summarises the submissions of a certain user and
    exercise. It calculates some characterizing figures such as the number of
    submissions and reference to the best submission. See the public methods
    for more.
    """
    def __init__(self, exercise, user=None):
        self.exercise = exercise
        self.max_points = getattr(exercise, 'max_points', 0)
        self.difficulty = getattr(exercise, 'difficulty', '')
        self.points_strategy = exercise.submission_in_effect
        self.points_to_pass = getattr(exercise, 'points_to_pass', 0)
        self.user = user
        self.submissions = []
        self.submission_count = 0
        self.effective_submission = None
        self.graded = False
        self.unofficial = False

        if self.user and self.user.is_authenticated():
            self.submissions = list(exercise.get_submissions_for_student(
                user.userprofile))

            # If latest submission should be in effect, make it such.
            if self.submissions and self.points_strategy == "L":
                self.effective_submission = self.submissions[0]

            for s in self.submissions:
                if not s.status in (
                    Submission.STATUS.ERROR,
                    Submission.STATUS.REJECTED,
                ):
                    self.submission_count += 1
                    if (
                        s.status == Submission.STATUS.READY and (
                            self.effective_submission is None
                            or self.unofficial
                            or (s.grade > self.effective_submission.grade and self.points_strategy == "B")
                        )
                    ):
                        self.effective_submission = s
                        self.unofficial = False
                        self.graded = True
                    elif (
                        s.status == Submission.STATUS.UNOFFICIAL and (
                            not self.graded
                            or (
                                self.unofficial
                                and s.grade > self.effective_submission.grade and self.points_strategy == "B"
                            )
                        )
                    ):
                        self.effective_submission = s
                        self.unofficial = True

    def get_submission_count(self):
        return self.submission_count

    def get_submissions(self):
        return self.submissions

    def get_best_submission(self):
        return self.effective_submission

    def get_points(self):
        return self.effective_submission.grade if self.effective_submission else 0

    def get_penalty(self):
        return self.effective_submission.late_penalty_applied if self.effective_submission else None

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

    def get_group(self):
        if self.submission_count > 0:
            s = self.submissions[0]
            if s.submitters.count() > 0:
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
        self.exercises = list(BaseExercise.objects \
            .filter(course_module__course_instance=course_instance) \
            .order_by("course_module__closing_time", "course_module", "order"))
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


    def __collect_student_grades(self):
        """
        Helper for the __init__.
        This method puts the data from the database in to the results table.
        """

        # Submissions for a given course instance.
        course_submissions = Submission.objects.filter(exercise__course_module__course_instance=self.course_instance,
            status=Submission.STATUS.READY)

        # Group the data by given attributes and compute best score and id of latest submission.
        submissions = course_submissions \
            .values("submitters", "exercise", "exercise__category", "exercise__submission_in_effect") \
            .annotate(best=Max("grade"), newest=Max("id")) \
            .order_by() # Remove default ordering.

        for submission in list(submissions):
            student_id = submission["submitters"]
            if student_id in self.results:
                # Get the score for the latest submission or the already computed best score,
                # based on the exercise configuration.
                grade = (course_submissions.get(id=submission["newest"]).grade
                 if submission["exercise__submission_in_effect"] == "L" else submission["best"])
                self.results[student_id][submission["exercise"]] = grade
                self.results_by_category[student_id][submission["exercise__category"]] += grade


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
