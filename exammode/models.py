from django.db import models
from django.urls import reverse
from django.utils import timezone

from course.models import CourseInstance, CourseModule
from exercise.exercise_models import LearningObject
from userprofile.models import UserProfile


class ActiveExamSessionManager(models.Manager):
    # FIXME: Using duration field in the filter query was much more problematic
    # than expected, due to it's usage in the datetime field. Similar situations
    # where handled often with raw sql. However, we propably don't need to deal
    # with this problem at all, since we will get rid of the current time management
    # and start using the modules starting and closing times.
    def active_exams(self):
        initial_queryset = super().get_queryset()
        queryset = [q for q in initial_queryset if q.exam_module.is_open()]
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
    exam_manager = ActiveExamSessionManager()

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
            redirect_url = learning_objects[0].get_display_url()

        else:
            return reverse("exam_module_not_defined")

        attempt = ExamAttempt(
            exam_taken=self,
            student=user.userprofile,
            exam_started=timezone.now()
        )
        attempt.save()

        user.userprofile.active_exam = attempt
        user.userprofile.save()

        return redirect_url

    def get_url(self):
        learning_objects = LearningObject.objects.filter(
            course_module__exact=self.exam_module
        )
        if learning_objects:
            return learning_objects[0].get_display_url()

        else:
            return reverse("exam_module_not_defined")

    def end_exam(self, user):
        attempt = ExamAttempt.objects.filter(
            exam_taken=self, student=user.userprofile)[:1].get()
        attempt.exam_finished = timezone.now()
        attempt.save()

        user.userprofile.active_exam = None
        user.userprofile.save()

        redirect_url = ("exam_final_info")

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
