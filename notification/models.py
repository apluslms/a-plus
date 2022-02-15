from django.db import models
from django.utils.translation import gettext_lazy as _

from course.models import CourseInstance
from exercise.models import Submission
from lib.models import UrlMixin
from userprofile.models import UserProfile


class Notification(UrlMixin, models.Model):
    """
    A user notification of some event, for example manual assessment.
    """
    subject = models.CharField(
        verbose_name=_('LABEL_SUBJECT'),
        max_length=255,
        blank=True,
    )
    notification = models.TextField(
        verbose_name=_('LABEL_NOTIFICATION'),
        blank=True,
    )
    sender = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_SENDER'),
        on_delete=models.SET_NULL,
        related_name="sent_notifications",
        blank=True, null=True,
    )
    recipient = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_RECIPIENT'),
        on_delete=models.CASCADE,
        related_name="received_notifications",
    )
    timestamp = models.DateTimeField(
        verbose_name=_('LABEL_TIMESTAMP'),
        auto_now_add=True,
    )
    seen = models.BooleanField(
        verbose_name=_('LABEL_SEEN'),
        default=False,
    )
    course_instance = models.ForeignKey(CourseInstance,
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
    )
    submission = models.ForeignKey(Submission,
        verbose_name=_('LABEL_SUBMISSION'),
        on_delete=models.CASCADE,
        related_name="notifications",
        blank=True, null=True,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_NOTIFICATION')
        verbose_name_plural = _('MODEL_NAME_NOTIFICATION_PLURAL')
        ordering = ['-timestamp']

    def __str__(self):
        return (
            "To:" + self.recipient.user.username + ", "
            + (str(self.submission.exercise) if self.submission else self.subject)
        )

    @classmethod
    def send(cls, sender: UserProfile, submission: Submission) -> None:
        for recipient in submission.submitters.all():
            if not Notification.objects.filter(
                submission=submission,
                recipient=recipient,
                seen=False,
            ).exists():
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
