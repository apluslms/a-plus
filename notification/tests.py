from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from course.models import Course, CourseInstance
from notification.models import Notification, NotificationSet


class NotificationTest(TestCase):
    def setUp(self):
        self.student = User(username="testUser", first_name="Superb", last_name="Student", email="test@aplus.com")
        self.student.set_password("testPassword")
        self.student.save()
        self.student_profile = self.student.userprofile

        self.teacher = User(username="teacher", first_name="Tedious", last_name="Teacher", email="teacher@aplus.com", is_staff=True)
        self.teacher.set_password("teacherPassword")
        self.teacher.save()
        self.teacher_profile = self.teacher.userprofile

        self.superuser = User(username="superuser", first_name="Super", last_name="User", email="superuser@aplus.com", is_superuser=True)
        self.superuser.set_password("superuserPassword")
        self.superuser.save()
        self.superuser_profile = self.superuser.userprofile

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )
        self.course.teachers.add(self.teacher.userprofile)

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

        self.course_instance2 = CourseInstance.objects.create(
            instance_name="Fall 2011 day 2",
            website="http://www.example.com",
            starting_time=self.tomorrow,
            ending_time=self.two_days_from_now,
            course=self.course,
            url="T-00.1000_d2"
        )

        self.notification = Notification.objects.create(
            subject="testSubject",
            notification="testNotification",
            sender=self.student.userprofile,
            recipient=self.teacher.userprofile,
            course_instance=self.course_instance
        )

    def test_notification_send(self):
        notifications = Notification.objects.all()
        self.assertEqual(1, len(notifications))
        self.assertEqual(self.student.userprofile, notifications[0].sender)
        self.assertEqual(self.teacher.userprofile, notifications[0].recipient)
        self.assertEqual(self.course_instance, notifications[0].course_instance)
        self.assertEqual("testSubject", notifications[0].subject)
        self.assertEqual("testNotification", notifications[0].notification)
        self.assertFalse(notifications[0].seen)

        Notification.send(self.teacher.userprofile, self.student.userprofile, self.course_instance, "subject", "notification")
        notifications = Notification.objects.all()
        self.assertEqual(2, len(notifications))
        self.assertEqual(self.teacher.userprofile, notifications[0].sender)
        self.assertEqual(self.student.userprofile, notifications[0].recipient)
        self.assertEqual(self.course_instance, notifications[0].course_instance)
        self.assertEqual("subject", notifications[0].subject)
        self.assertEqual("notification", notifications[0].notification)
        self.assertFalse(notifications[0].seen)
        self.assertEqual(self.student.userprofile, notifications[1].sender)
        self.assertEqual(self.teacher.userprofile, notifications[1].recipient)
        self.assertEqual(self.course_instance, notifications[1].course_instance)
        self.assertEqual("testSubject", notifications[1].subject)
        self.assertEqual("testNotification", notifications[1].notification)
        self.assertFalse(notifications[1].seen)

    def test_notification_mark_as_seen(self):
        self.assertFalse(self.notification.seen)
        ns = NotificationSet.get_unread(self.teacher)
        self.assertEqual(ns.count, 1)
        ns = NotificationSet.get_course_unread_and_mark(self.course_instance, self.teacher)
        self.assertTrue(self.notification in ns.notifications)
        ns = NotificationSet.get_unread(self.teacher)
        self.assertEqual(ns.count, 0)
        ns = NotificationSet.get_course_read(self.course_instance, self.teacher)
        self.assertEqual(ns.count, 1)

    def test_notification_string(self):
        self.assertEqual("To:teacher, testSubject, testNotification", str(self.notification))

    def test_notification_unread_count(self):
        
        self.notification1 = Notification.objects.create(
            subject="test1",
            notification="testNotification1",
            sender=self.superuser_profile,
            recipient=self.student_profile,
            course_instance=self.course_instance
        )

        self.notification2 = Notification.objects.create(
            subject="test2",
            notification="testNotification2",
            sender=self.superuser_profile,
            recipient=self.teacher_profile,
            course_instance=self.course_instance
        )

        self.notification3 = Notification.objects.create(
            subject="test3",
            notification="testNotification3",
            sender=self.superuser_profile,
            recipient=self.student_profile,
            course_instance=self.course_instance2
        )

        self.notification4 = Notification.objects.create(
            subject="test4",
            notification="testNotification4",
            sender=self.superuser_profile,
            recipient=self.teacher_profile,
            course_instance=self.course_instance
        )

        self.notification5 = Notification.objects.create(
            subject="test5",
            notification="testNotification5",
            sender=self.superuser_profile,
            recipient=self.student_profile,
            course_instance=self.course_instance2
        )
        self.notification.seen = True
        self.notification.save()
        unread = NotificationSet.get_unread(self.student)
        self.assertEqual(3, unread.count)
        unread = NotificationSet.get_unread(self.teacher)
        self.assertEqual(2, unread.count)
        unread = NotificationSet.get_unread(self.superuser)
        self.assertEqual(0, unread.count)

    def test_notification_unread_course_instances(self):
        unread = NotificationSet.get_unread(self.teacher)
        self.assertEqual(1, unread.count)
        self.assertTrue(self.course_instance in unread.course_instances)
