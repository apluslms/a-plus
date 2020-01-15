from django.db import models
from django.urls import reverse
from django.utils import timezone

from course.models import CourseInstance, CourseModule
from exercise.exercise_models import LearningObject
from userprofile.models import UserProfile


class ActiveExamSessionManager(models.Manager):

    def get_queryset(self):
        initial_queryset = super().get_queryset()
        queryset = initial_queryset.filter(
            exam_module__opening_time__lte=timezone.now()
                ).filter(
            exam_module__closing_time__gte=timezone.now()
                )
        return queryset


class ExamSession(models.Model):
    """
    Represents one instance of a course exam
    """

    name = models.CharField(max_length=255, blank=False, default=None)
    course_instance = models.ForeignKey(
        CourseInstance, on_delete=models.CASCADE)
    exam_module = models.ForeignKey(
        CourseModule, on_delete=models.CASCADE, blank=False, default=None)
    room = models.CharField(max_length=255, null=True, blank=True)

    objects = models.Manager()
    active_exams = ActiveExamSessionManager()

    class Meta:
        unique_together = [['name', 'room']]

    def __str__(self):
        return " ".join([str(self.exam_module), str(self.room)])

    def start_exam(self, user):

        # Checking first if exam content is available. If not, database entries would be pointless
        learning_objects = LearningObject.objects.filter(
            course_module__exact=self.exam_module
        )

        if learning_objects:
            redirect_url = learning_objects[0].get_exam_url()

        else:
            return reverse("exam_module_not_defined")

        attempt = ExamAttempt.objects.create(
            exam_taken=self,
            student=user.userprofile,
            exam_started=timezone.now()
        )

        user.userprofile.active_exam = attempt
        user.userprofile.save()

        return redirect_url

    def get_url(self):
        learning_objects = LearningObject.objects.filter(
            course_module__exact=self.exam_module
        )
        if learning_objects:
            return learning_objects[0].get_exam_url()
        else:
            return reverse("exam_module_not_defined")

    def end_exam(self, user):
        redirect_url = ("exam_final_info")
        attempt = user.userprofile.active_exam
        if not attempt:
            return redirect_url
        attempt.exam_finished = timezone.now()
        attempt.save()

        user.userprofile.active_exam = None
        user.userprofile.save()

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

    objects = models.Manager()

    def __str__(self):
        return " ".join([str(self.exam_taken), str(self.student)])
