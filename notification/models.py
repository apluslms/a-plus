from django.db import models

from course.models import CourseInstance
from userprofile.models import UserProfile


class NotificationSet(object):
    """
    A result set of notifications.
    
    """
    @classmethod
    def get_unread(cls, user):
        return NotificationSet(
            user.userprofile.received_notifications.filter(
                seen=False))

    @classmethod
    def get_course_unread_and_mark(cls, course_instance, user):
        qs = user.userprofile.received_notifications.filter(
            course_instance=course_instance,
            seen=False)
        notifications = list(qs)
        qs.update(seen=True)
        return NotificationSet(notifications)

    @classmethod
    def get_course_read(cls, course_instance, user):
        return NotificationSet(
            user.userprofile.received_notifications.filter(
                course_instance=course_instance,
                seen=True))

    def __init__(self, queryset):
        self.notifications = list(queryset)
    
    @property
    def count(self):
        return len(self.notifications)
    
    @property
    def course_instances(self):
        courses = set()
        for notification in self.notifications:
            courses.add(notification.course_instance)
        return courses


class Notification(models.Model):
    """
    A user notification of some event, for example manual assessment.
    """

    @classmethod
    def send(cls, sender, recipient, course_instance, subject, notification):
        notification = Notification(
            notification=notification,
            subject=subject,
            sender=sender,
            recipient=recipient,
            course_instance=course_instance
        )
        notification.save()

    subject = models.CharField(max_length=255)
    notification = models.TextField()
    sender = models.ForeignKey(UserProfile, related_name="sent_notifications")
    recipient = models.ForeignKey(UserProfile, related_name="received_notifications")
    timestamp = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)
    course_instance = models.ForeignKey(CourseInstance)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return "To:" + self.recipient.user.username + ", " + self.subject + ", " + self.notification[:100]
