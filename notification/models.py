from django.db import models

from course.models import CourseInstance
from userprofile.models import UserProfile


class UnreadNotifications(object):
    """
    Represents the unread notifications for a user.
    """

    @classmethod
    def get_for(cls, user):
        return UnreadNotifications(user)
    
    def __init__(self, user):
        self.notifications = list(user.userprofile.received_notifications.filter(seen=False))
    
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
        notification = Notification(notification=notification, subject=subject, sender=sender, recipient=recipient, course_instance=course_instance)
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

    def mark_as_seen(self):
        self.seen = True
        self.save()
