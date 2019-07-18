from django.db import models
from django.utils import timezone

from course.models import CourseInstance
from userprofile.models import UserProfile

# Create your models here.


class ExamSession(models.Model):
    """
    Represents one instance of a course exam
    """

    course_instance = models.ForeignKey(
        CourseInstance, on_delete=models.CASCADE)
    can_start = models.DateTimeField(editable=True, default=timezone.now)
    duration = models.IntegerField()
    start_time_actual = models.DateTimeField(
        editable=True, default=timezone.now)
    may_leave_time = models.DateTimeField(editable=True, default=timezone.now)
    room = models.CharField(max_length=255)

    def __str__(self):
        # return self.course_instance
        return " ".join([str(self.course_instance), str(self.can_start)])

    def can_start_now(self):
        return self.can_start <= timezone.now() and timezone.now() <= self.can_start + timezone.timedelta(self.duration)


class ExamAttempt(models.Model):
    exam_taken = models.ForeignKey(ExamSession, on_delete=models.CASCADE)
    student = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    exam_started = models.DateTimeField(
        auto_now_add=True)
    exam_finished = models.DateTimeField(editable=True, default=timezone.now)

    # Placeholder to store system / hw indentifying data. Could be used for invigilating purposes
    # TODO: Implement how this is collected and used.
    system_identifier = models.CharField(max_length=255)

    """
    Stores reference to a specific set of exam questions. Allows personalisation of exams
    TODO: needs to be changed into actual model of exam which is unimplemented
    """
    exam_version = models.CharField(max_length=255)

    def __str__(self):
        return " ".join([str(self.exam_taken), str(self.student)])
