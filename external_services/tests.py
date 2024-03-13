from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from course.models import Course, CourseInstance
from userprofile.models import User
from .cache import CachedCourseMenu
from .models import LinkService, LTIService, MenuItem


class ExternalServicesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User(username="testUser")
        cls.user.set_password("testPassword")
        cls.user.save()

        cls.assistant = User(username="testUser2")
        cls.assistant.set_password("testPassword")
        cls.assistant.save()

        cls.link_service = LinkService.objects.create(
            url="http://www.external-service.com",
            destination_region=LinkService.DESTINATION_REGION.INTERNAL,
            menu_label="External Service"
        )

        cls.disabled_link_service = LinkService.objects.create(
            url="http://www.disabled-external-service.com",
            destination_region=LinkService.DESTINATION_REGION.INTERNAL,
            menu_label="Disabled External Service",
            enabled=False
        )
        cls.lti_service = LTIService.objects.create(
            url="http://www.lti-service.com",
            destination_region=LinkService.DESTINATION_REGION.INTERNAL,
            menu_label="LTI Service",
            menu_icon_class="star",
            access_settings = LTIService.LTI_ACCESS.PUBLIC_API_NO,
            consumer_key="123456789",
            consumer_secret="987654321"
        )

        cls.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        cls.today = timezone.now()
        cls.tomorrow = cls.today + timedelta(days=1)

        cls.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011",
            starting_time=cls.today,
            ending_time=cls.tomorrow,
            course=cls.course,
            url="T-00.1000_2011"
        )
        cls.course_instance.enroll_student(cls.user)
        cls.course_instance.add_assistant(cls.assistant.userprofile)

        cls.menu_item1 = MenuItem.objects.create(
            service=cls.link_service,
            course_instance=cls.course_instance,
            access=MenuItem.ACCESS.STUDENT,
            menu_label="Overriden Label",
            menu_icon_class="star"
        )

        cls.menu_item2 = MenuItem.objects.create(
            service=cls.link_service,
            course_instance=cls.course_instance,
            access=MenuItem.ACCESS.STUDENT,
            enabled=False
        )

        cls.menu_item3 = MenuItem.objects.create(
            service=cls.disabled_link_service,
            course_instance=cls.course_instance,
            access=MenuItem.ACCESS.STUDENT
        )

        cls.menu_item4 = MenuItem.objects.create(
            service=cls.lti_service,
            course_instance=cls.course_instance,
            access=MenuItem.ACCESS.STUDENT
        )

        cls.menu_item5 = MenuItem.objects.create(
            service=cls.lti_service,
            course_instance=cls.course_instance,
            access=MenuItem.ACCESS.ASSISTANT
        )

    def test_menuitem_label(self):
        self.assertEqual("Overriden Label", self.menu_item1.label)
        self.assertEqual("External Service", self.menu_item2.label)
        self.assertEqual("Disabled External Service", self.menu_item3.label)
        self.assertEqual("LTI Service", self.menu_item4.label)
        self.assertEqual("LTI Service", self.menu_item5.label)

    def test_menuitem_icon_class(self):
        self.assertEqual("star", self.menu_item1.icon_class)
        self.assertEqual("globe", self.menu_item2.icon_class)
        self.assertEqual("globe", self.menu_item3.icon_class)
        self.assertEqual("star", self.menu_item4.icon_class)
        self.assertEqual("star", self.menu_item5.icon_class)

    def test_menuitem_url(self):
        self.assertEqual("http://www.external-service.com", self.menu_item1.url)
        self.assertEqual("http://www.external-service.com", self.menu_item2.url)
        self.assertEqual("http://www.disabled-external-service.com", self.menu_item3.url)
        self.assertEqual("/Course-Url/T-00.1000_2011/lti-login/4/", self.menu_item4.url)
        self.assertEqual("/Course-Url/T-00.1000_2011/lti-login/5/", self.menu_item5.url)

    def test_view(self):
        url = self.menu_item4.url
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username="testUser", password="testPassword")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("oauth_signature" in str(response.content, encoding='utf-8'))

        url = self.menu_item5.url
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username="testUser2", password="testPassword")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.menu_item5.access = MenuItem.ACCESS.TEACHER
        self.menu_item5.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.course_instance.add_teacher(self.assistant.userprofile)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_cached(self):
        menu = CachedCourseMenu(self.course_instance)
        self.assertEqual(len(menu.student_link_groups()), 1)
        self.assertEqual(len(menu.student_link_groups()[0]['items']), 4)
        self.assertEqual(len(menu.staff_link_groups()), 1)
        self.assertEqual(len(menu.staff_link_groups()[0]['items']), 1)
