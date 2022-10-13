from lib.testdata import CourseTestCase
from .cache import CachedNotifications
from .models import Notification


class NotificationTest(CourseTestCase):

    def test_notifications(self):
        Notification.send(self.teacher.userprofile, self.submission)
        Notification.send(None, self.submission)
        Notification.send(None, self.submission3)

        cn = CachedNotifications(self.student)
        self.assertEqual(cn.count(), 2)
        cn = CachedNotifications(self.user)
        self.assertEqual(cn.count(), 1)

        n = Notification.objects.get(id=cn.notifications()[0]['id'])
        n.seen = True
        n.save()
        cn = CachedNotifications(None)
        self.assertEqual(cn.count(), 0)
        cn = CachedNotifications(self.user)
        self.assertEqual(cn.count(), 0)
        cn = CachedNotifications(self.student)
        self.assertEqual(cn.count(), 2)

        for n in cn.notifications():
            if n['submission_id'] == self.submission.id:
                n = Notification.objects.get(id=n['id'])
                n.seen = True
                n.save()
                break
        cn = CachedNotifications(self.student)
        self.assertEqual(cn.count(), 1)

        Notification.remove(self.submission3)
        cn = CachedNotifications(self.student)
        self.assertEqual(cn.count(), 0)
