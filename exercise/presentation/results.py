from django.db.models import Max

from exercise.models import BaseExercise, Submission


class ResultTable:
    """
    Models the table displaying the grades for each student on each exercise.
    ResultTables are generated dynamically when needed and not stored
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

        # Students on the course.
        self.students = list(course_instance.get_student_profiles())

        # Empty results table.
        self.results = {
            student.id: {
                exercise.id: None for exercise in self.exercises
            } for student in self.students
        }

        # Fill the results with the data from the database.
        self.__collect_student_grades()


    def __collect_student_grades(self):
        """
        Helper for the __init__.
        This method puts the data from the database in to the results table.
        """
        submissions = list(Submission.objects \
            .filter(exercise__course_module__course_instance=self.course_instance) \
            .values("submitters", "exercise") \
            .annotate(best=Max("grade")) \
            .order_by()) # Remove default ordering.
        for submission in submissions:
            student_id = submission["submitters"]
            if student_id in self.results:
                self.results[student_id][submission["exercise"]] = submission["best"]


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
