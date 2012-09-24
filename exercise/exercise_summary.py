# Python
from datetime import datetime

# Django
from django.utils import simplejson
from django.db.models.aggregates import Avg, Max, Sum

# A+
from exercise.exercise_models import *

class ExerciseSummary:
    def __init__(self, exercise, user):
        self.exercise           = exercise
        self.user               = user
        self.submission_count   = 0
        self.best_submission    = None
        
        self._generate_summary()
    
    def _generate_summary(self):
        """
        Initializes the instance variables submission_count and best_submission.
        The best submission is the submission with the highest grade and latest id.
        """
        submissions             = self.exercise.get_submissions_for_student(self.user.get_profile())
        self.submission_count   = submissions.count()
        
        if self.submission_count != 0:
            self.best_submission = submissions.order_by("-grade", "-id")[0]
    
    def get_max_points(self):
        return self.exercise.max_points
    
    def get_points(self):
        if self.best_submission == None:
            return 0
        return self.best_submission.grade
    
    def get_completed_percentage(self):
        if self.get_max_points() == 0:
            return 0
        else:
            return int(round(100.0 * self.get_points() / self.get_max_points()))
    
    def get_required_percentage(self):
        if self.get_max_points() == 0:
            return 0
        else:
            return int(round(100.0 * self.exercise.points_to_pass / self.get_max_points()))
    
    def get_average_percentage(self):
        if self.get_max_points() == 0:
            return 0
        else:
            return int(round(100.0 * self.exercise.summary["average_grade"] / self.get_max_points()))
    
    def is_full_points(self):
        return self.get_points() == self.exercise.max_points
    
    def is_passed(self):
        return self.get_points() >= self.exercise.points_to_pass

class ExerciseRoundSummary:
    def __init__(self, exercise_round, user):
        self.exercise_round     = exercise_round
        self.user               = user
        self.exercises          = BaseExercise.objects.filter(course_module=exercise_round)
        self.points_available   = 0
        self.exercises_passed   = 0
        self.exercise_summaries = []
        
        self._generate_summary()
    
    def _generate_summary(self):
        for exercise in self.exercises:
            self.exercise_summaries.append( ExerciseSummary(exercise, self.user) ) 
    
    def get_total_points(self):
        total                   = 0
        for ex_summary in self.exercise_summaries:
            total += ex_summary.get_points()
        return total
    
    def get_maximum_points(self):
        total                   = 0
        for ex_summary in self.exercise_summaries:
            total += ex_summary.get_max_points()
        return total
    
    def get_average_total_grade(self):
        return sum([exercise.summary["average_grade"] for exercise in self.exercises])
    
    def is_passed(self):
        """
        Returns True or False based on if the student has passed the exercise round
        or not. The round is passed if the total points are equal to or higher than
        minimum for the round and if each individual exercise in the round is passed.
        """
        if self.get_total_points() < self.exercise_round.points_to_pass:
            return False
        
        for es in self.exercise_summaries:
            if not es.is_passed():
                return False
        
        return True
    
    def get_exercise_count(self):
        return self.exercises.count()
    
    def get_classes(self):
        """
        Returns the CSS classes that should be used for 
        this exercise round in the exercise view.
        """
        classes = []
        if self.exercise_round.opening_time > datetime.now():
            classes.append("upcoming")
            classes.append("collapsed")
        
        elif self.exercise_round.closing_time < datetime.now():
            classes.append("closed")
            classes.append("collapsed")
        
        else:
            classes.append("open")
        
        return " ".join(classes)


class CourseSummary:
    """ 
    Course summary generates a personal summary for a user of the exercises
    existing and completed on a given course. 
    """
    def __init__(self, course_instance, user):
        self.course_instance        = course_instance
        self.user                   = user
        self.exercise_rounds        = course_instance.course_modules.all()
        self.round_summaries        = []
        
        self._generate_summary()
    
    def is_passed(self):
        for round_summary in self.round_summaries:
            if round_summary.is_passed() == False:
                return False
        return True
    
    def get_exercise_count(self):
        exercise_count = 0
        for round_summary in self.round_summaries:
            exercise_count += round_summary.get_exercise_count()
        return exercise_count
    
    def get_maximum_points(self):
        """
        Returns the maximum points for the whole course instance, ie. the sum of 
        maximum points for all exercises.
        """
        all_exercises   = BaseExercise.objects.filter(course_module__course_instance=self.course_instance)
        max_points      = all_exercises.aggregate(max_points=Sum('max_points'))['max_points']
        return max_points or 0
    
    def get_total_points(self):
        point_sum = 0
        for ex_round in self.round_summaries:
            point_sum += ex_round.get_total_points()
        return point_sum
    
    def get_json_by_rounds(self):
        round_list = []
        for round_summary in self.round_summaries:
            round_list.append( [round_summary.exercise_round.name, 
                                round_summary.get_total_points(),
                                round_summary.get_average_total_grade(),
                                round_summary.get_maximum_points(),
                                ])
        return simplejson.dumps(round_list)
    
    def get_completed_percentage(self):
        max_points = self.get_maximum_points()
        if max_points == 0:
            return 0
        else:
            return int(round(100.0 * self.get_total_points() / max_points))
    
    def _generate_summary(self):
        # Generate a summary of each exercise round
        for rnd in self.exercise_rounds:
            self.round_summaries.append( ExerciseRoundSummary(rnd, self.user) )
