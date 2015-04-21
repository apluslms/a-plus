from django.test import TestCase

from notification.models import *
from userprofile.models import *
from course.models import *

from datetime import datetime, timedelta

class NotificationTest(TestCase):
    def setUp(self):
        self.student = User(username="testUser", first_name="Superb", last_name="Student", email="test@aplus.com")
        self.student.set_password("testPassword")
        self.student.save()

        self.teacher = User(username="teacher", first_name="Tedious", last_name="Teacher", email="teacher@aplus.com", is_staff=True)
        self.teacher.set_password("teacherPassword")
        self.teacher.save()

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )
        self.course.teachers.add(self.teacher.get_profile())

        self.today = datetime.now()
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.tomorrow + timedelta(days=1)

        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011",
            website="http://www.example.com",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_2011"
        )

        self.notification = Notification.objects.create(
            subject="testSubject",
            notification="testNotification",
            sender=self.student.get_profile(),
            recipient=self.teacher.get_profile(),
            course_instance=self.course_instance
        )

    def test_notification_send(self):
        notifications = Notification.objects.all()
        self.assertEqual(1, len(notifications))
        self.assertEqual(self.student.get_profile(), notifications[0].sender)
        self.assertEqual(self.teacher.get_profile(), notifications[0].recipient)
        self.assertEqual(self.course_instance, notifications[0].course_instance)
        self.assertEqual("testSubject", notifications[0].subject)
        self.assertEqual("testNotification", notifications[0].notification)
        self.assertFalse(notifications[0].seen)

        Notification.send(self.teacher.get_profile(), self.student.get_profile(), self.course_instance, "subject", "notification")
        notifications = Notification.objects.all()
        self.assertEqual(2, len(notifications))
        self.assertEqual(self.teacher.get_profile(), notifications[0].sender)
        self.assertEqual(self.student.get_profile(), notifications[0].recipient)
        self.assertEqual(self.course_instance, notifications[0].course_instance)
        self.assertEqual("subject", notifications[0].subject)
        self.assertEqual("notification", notifications[0].notification)
        self.assertFalse(notifications[0].seen)
        self.assertEqual(self.student.get_profile(), notifications[1].sender)
        self.assertEqual(self.teacher.get_profile(), notifications[1].recipient)
        self.assertEqual(self.course_instance, notifications[1].course_instance)
        self.assertEqual("testSubject", notifications[1].subject)
        self.assertEqual("testNotification", notifications[1].notification)
        self.assertFalse(notifications[1].seen)

    def test_notification_mark_as_seen(self):
        self.assertFalse(self.notification.seen)
        self.notification.mark_as_seen()
        self.assertTrue(self.notification.seen)

    def test_notification_string(self):
        self.assertEqual("To:teacher, testSubject, testNotification", str(self.notification))