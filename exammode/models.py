from django.db import models

from course.models import CourseInstance
from userprofile.models import UserProfile

# Create your models here.


class ExamSession(models.Model):
    """
    Represents one instance of a course exam
    """

    course_instance = models.ForeignKey(
        CourseInstance, on_delete=models.CASCADE)
    start_time = models.DateTimeField
    end_time = models.DateTimeField
    start_time_actual = models.DateTimeField
    end_time_actual = models.DateTimeField
    may_leave_time = models.DateTimeField
    room = models.CharField(max_length=255)


class ExamTaken(models.Model):
    """
    Represents one student taking part in one exam session.
    """

    exam_taken = models.ForeignKey(ExamSession, on_delete=models.CASCADE)
    student = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    exam_started = models.DateTimeField(auto_now_add=True)
    exam_finished = models.DateTimeField

    """
    Stores reference to a specific set of exam questions. Allows personalisation of exams
    TODO: needs to be changed into actual model of exam which is unimplemented
    """
    exam_version = models.CharField(max_lenght=255)
