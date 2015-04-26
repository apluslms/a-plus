# A+
from userprofile.models import UserProfile
from exercise.exercise_models import BaseExercise, CourseModule
from exercise.submission_models import Submission

# Django
from django.db.models import Max

class ResultTable:
    """
    ResultTable is a class that models the table displaying the grades for each student
    on each exercise. ResultTables are generated dynamically when needed and not stored
    in a database.
    """

    def __init__(self, course_instance):
        """
        Instantiates a new ResultTable for the given course instance.
        After initialization the table is filled with grades from the database.

        @param course_instance: The CourseInstance model that we wish to get grades from
        """

        self.course_instance    = course_instance

        # Find the best submissions for each user-exercise combination.
        # This generates a list of dicts with the keys "student_id",
        # "submissions__exercise" and "submissions__grade".
        # Note that the "submitters" key does not contain a list but an id of a
        # single UserProfile model instance.
        self.best_submissions = Submission.objects.filter(
            exercise__course_module__course_instance=course_instance).exclude(
                submitters=None).values("submitters", "exercise").annotate(
                    best=Max("grade")).order_by()

        # self.best_submissions elements only contain the id of the exercise.
        # We need other exercise data too so we fetch the related BaseExercise
        # instances too.
        # Note that these are ordered.
        self.exercises = BaseExercise.objects.filter(
            course_module__course_instance=course_instance).order_by(
            "course_module__closing_time", "course_module", "order")

        # self.best_submissions elements only contain the id of the user
        # profile.
        # We need other user data too so we fetch the related UserProfiles
        # instances too.
        self.students = UserProfile.objects.filter(
            submissions__exercise__course_module__course_instance\
            =course_instance).distinct()

        # The data is converted to a dictionary of dictionaries where the outer
        # dictionaries have UserProfile model instances as keys and the
        # sub-dictionaries have BaseExercise model instances as keys.
        self.results = {}
        # Fill the results with the data from the database.
        self.__collect_student_grades()


    def __collect_student_grades(self):
        """
        Helper for the __init__.
        This method puts the data from the database in to the results table.
        """

        # Lets force the QuerySets to evaluate
        students_by_id = {student.id: student for student in self.students}
        exercises_by_id =\
                {exercise.id: exercise for exercise in self.exercises}

        for submission in self.best_submissions:
            student = students_by_id[submission["submitters"]]
            exercise = exercises_by_id[submission["exercise"]]
            # Create empty dict for this student if he already isn't in the
            # results table.
            if not student in self.results:
                self.results[student] = {ex: None for ex in self.exercises}

            # Put the best submission record to the results table.
            self.results[student][exercise] = submission["best"]


    def results_for_template(self):
        """
        Converts the results data into a form that is convenient for to use in a
        template. The columns of the table ordered according to the order of the
        exercises in self.exercises.
        @return: the template-friendly data structure of the ResultTable data
        """
        for_template = []
        for student, grades_d in list(self.results.items()):
            grades = []
            sum = 0
            for ex in self.exercises:
                grade = grades_d[ex]
                if grade: sum += grade
                grades.append(grade)
            for_template.append((student, grades, sum, ))
        return for_template


    def max_sum(self):
        """
        @return: returns the sum of maximum points of all the exercises
        """
        sum = 0
        for ex in self.exercises:
            sum += ex.max_points
        return sum
