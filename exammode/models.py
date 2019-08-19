from django.db import models
from django.utils import timezone

from course.models import CourseInstance, CourseModule
from exercise.exercise_models import LearningObject
from userprofile.models import UserProfile

# Create your models here.

class ExamSessionManager(models.Manager):

    def get_queryset(self):
        initial_queryset = super().get_queryset()
        queryset = [q for q in initial_queryset if (
            q.can_start <= timezone.now())]

        return queryset

    def is_active(self):
        initial_queryset = super().get_queryset()
        queryset = [q for q in initial_queryset if (q.can_start <= timezone.now(
        ) and (timezone.now() <= q.can_start + timezone.timedelta(hours=q.duration)))]

        return queryset


class ExamSession(models.Model):
    """
    Represents one instance of a course exam
    """

    course_instance = models.ForeignKey(
        CourseInstance, on_delete=models.CASCADE)
    exam_module = models.ForeignKey(
        CourseModule, on_delete=models.CASCADE, null=True)
    can_start = models.DateTimeField(editable=True, default=timezone.now)
    duration = models.IntegerField()
    start_time_actual = models.DateTimeField(
        editable=True, default=timezone.now)
    may_leave_time = models.DateTimeField(editable=True, default=timezone.now)
    room = models.CharField(max_length=255)

    objects = models.Manager()
    active_exams = ExamSessionManager()

    def __str__(self):
        # return self.course_instance
        return " ".join([str(self.course_instance), str(self.can_start)])

    def start_exam(self, user):
        attempt = ExamAttempt(
            exam_taken=self,
            student=user.userprofile,
            exam_started=timezone.now()
        )
        attempt.save()

        user.userprofile.active_exam = attempt
        user.userprofile.save()

        learning_objects = LearningObject.objects.filter(
            course_module__exact=self.exam_module
        )

        module_url = self.exam_module.url
        if learning_objects:
            module_url +=  "/" + learning_objects[0].url

        redirect_url = (
            self.course_instance.course.url + "/"
            + self.course_instance.url + "/"
            + module_url
        )

        return redirect_url


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
