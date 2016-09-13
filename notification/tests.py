from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from course.models import Course, CourseInstance
from lib.testdata import CourseTestCase
from notification.models import Notification, NotificationSet


class NotificationTest(CourseTestCase):

    def test_notifications(self):
        Notification.send(self.teacher.userprofile, self.submission)
        Notification.send(None, self.submission)
        Notification.send(None, self.submission3)
        nset = NotificationSet.get_unread(self.student)
        self.assertEqual(nset.count, 3)
        nset = NotificationSet.get_unread(self.user)
        self.assertEqual(nset.count, 1)

        nset.notifications[0].seen = True
        nset.notifications[0].save()
        nset = NotificationSet.get_unread(None)
        self.assertEqual(nset.count, 0)
        nset = NotificationSet.get_unread(self.user)
        self.assertEqual(nset.count, 0)
        nset = NotificationSet.get_unread(self.student)
        self.assertEqual(nset.count, 3)

        for n in nset.notifications:
            if n.submission == self.submission:
                n.seen = True
                n.save()
                break
        nset = NotificationSet.get_unread(self.student)
        self.assertEqual(nset.count, 2)

        Notification.remove(self.submission)
        nset = NotificationSet.get_unread(self.student)
        self.assertEqual(nset.count, 1)
