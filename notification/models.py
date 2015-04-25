from course.models import *

class Notification(models.Model):

    subject         = models.CharField(max_length=255)
    notification    = models.TextField()
    sender          = models.ForeignKey(UserProfile, related_name="sent_notifications")
    recipient       = models.ForeignKey(UserProfile, related_name="received_notifications")
    timestamp       = models.DateTimeField(auto_now_add=True)
    seen            = models.BooleanField(default=False)
    course_instance = models.ForeignKey(CourseInstance)

    @classmethod
    def send(cls, sender, recipient, course_instance, subject, notification):
        notification = Notification(notification=notification, subject=subject, sender=sender, recipient=recipient, course_instance=course_instance)
        notification.save()

    def mark_as_seen(self):
        self.seen = True
        self.save()

    def __unicode__(self):
        return "To:" + self.recipient.user.username + ", " + self.subject + ", " + self.notification[:100]

    class Meta:
        ordering = ['-timestamp']
