from django.db import models

from course.models import CourseInstance
from exercise.models import Submission
from lib.models import UrlMixin
from userprofile.models import UserProfile


class Notification(UrlMixin, models.Model):
    """
    A user notification of some event, for example manual assessment.
    """
    subject = models.CharField(max_length=255, blank=True)
    notification = models.TextField(blank=True)
    sender = models.ForeignKey(UserProfile, on_delete=models.SET_NULL,
        related_name="sent_notifications", blank=True, null=True)
    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE,
        related_name="received_notifications")
    timestamp = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)
    course_instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE,
        related_name="notifications", blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return (
            "To:" + self.recipient.user.username + ", "
            + (str(self.submission.exercise) if self.submission else self.subject)
        )

    @classmethod
    def send(cls, sender, submission):
        for recipient in submission.submitters.all():
            if Notification.objects.filter(
                submission=submission,
                recipient=recipient,
                seen=False,
            ).count() == 0:
                notification = Notification(
                    sender=sender,
                    recipient=recipient,
                    course_instance=submission.exercise.course_instance,
                    submission=submission,
                )
                notification.save()

    @classmethod
    def remove(cls, submission):
        Notification.objects.filter(
            submission=submission,
            recipient__in=submission.submitters.all(),
            seen=False,
        ).delete()

    ABSOLUTE_URL_NAME = "notify"

    def get_url_kwargs(self):
        return dict(notification_id=self.id, **self.course_instance.get_url_kwargs())
