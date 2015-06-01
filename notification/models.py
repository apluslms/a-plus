from django.db import models

from course.models import CourseInstance
from userprofile.models import UserProfile


class Notification(models.Model):

    @classmethod
    def send(cls, sender, recipient, course_instance, subject, notification):
        notification = Notification(notification=notification, subject=subject, sender=sender, recipient=recipient, course_instance=course_instance)
        notification.save()

    @classmethod
    def get_unread_count(cls, user_profile):
        return len(user_profile.received_notifications.filter(seen=False))

    @classmethod
    def get_unread_course_instances(cls, user_profile):
        notifications = user_profile.received_notifications.filter(seen=False)
        courses = set()
        for notification in notifications:
            courses.add(notification.course_instance)
        return courses

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
