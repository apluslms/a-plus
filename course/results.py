# A+
from userprofile.models import UserProfile
from exercise.exercise_models import BaseExercise, CourseModule
from exercise.submission_models import Submission

# Django
from django.db.models import Q, Max

class ResultTable:
    """ 
    ResultTable is a class that models the table displaying the grades for each student
    on each exercise. ResultTables are generated dynamically when needed and not stored 
    in a database. 
    """
    
    def __init__(self, course_instance):
        """ 
        Instantiates a new ResutTable for the given course instance. 
        After initialization the table is filled with grades from the database.
        
        @param course_instance: The CourseInstance model that we wish to get grades from 
        """
        
        self.course_instance    = course_instance
        
        # Find all users (students) who have submitted anything to any of the exercises on this
        # course instance.
        user_query              = Q(submissions__exercise__course_module__course_instance=self.course_instance)
        self.students           = UserProfile.objects.distinct().filter(user_query)
        
        # Get modules and exercises
        self.modules            = CourseModule.objects.filter(course_instance=course_instance)
        self.exercises          = BaseExercise.objects.filter(course_module__in=self.modules)
        
        # Collect results for students and maximum points for each exercise on these lists
        self.results            = []
        self.max_points         = []
        
        # Fill the lists with data from database
        self.__collect_student_grades()
        self.__collect_maximum_points()
    
    def __collect_student_grades(self):
        """ 
        This method iterates through all students on the course and adds their scores 
        to the result table. 
        """
        
        for student in self.students:
            grades              = []
            
            for exercise in self.exercises:
                grade_query     = student.submissions.filter(exercise=exercise).aggregate(Max("grade"))
                grades.append(grade_query["grade__max"])
            
            # Count the total sum of grades. First filter None values from the list.
            grade_sum           = sum(filter(None, grades))
            self.results.append({ "student": student, "grades": grades, "grade_sum": grade_sum })
    
    def __collect_maximum_points(self):
        for exercise in self.exercises:
            self.max_points.append(exercise.max_points)
        
        # Add the sum of maximum points to the max points list
        self.max_points.append(sum(self.max_points))