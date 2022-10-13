from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from course.models import Course, CourseInstance
from userprofile.models import User
from .cache import CachedCourseMenu
from .models import LinkService, LTIService, MenuItem


class ExternalServicesTest(TestCase):
    def setUp(self):
        self.user = User(username="testUser")
        self.user.set_password("testPassword")
        self.user.save()

        self.assistant = User(username="testUser2")
        self.assistant.set_password("testPassword")
        self.assistant.save()

        self.link_service = LinkService.objects.create(
            url="http://www.external-service.com",
            destination_region=LinkService.DESTINATION_REGION.INTERNAL,
            menu_label="External Service"
        )

        self.disabled_link_service = LinkService.objects.create(
            url="http://www.disabled-external-service.com",
            destination_region=LinkService.DESTINATION_REGION.INTERNAL,
            menu_label="Disabled External Service",
            enabled=False
        )
        self.lti_service = LTIService.objects.create(
            url="http://www.lti-service.com",
            destination_region=LinkService.DESTINATION_REGION.INTERNAL,
            menu_label="LTI Service",
            menu_icon_class="star",
            access_settings = LTIService.LTI_ACCESS.PUBLIC_API_NO,
            consumer_key="123456789",
            consumer_secret="987654321"
        )

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        self.today = timezone.now()
        self.tomorrow = self.today + timedelta(days=1)

        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_2011"
        )
        self.course_instance.enroll_student(self.user)
        self.course_instance.add_assistant(self.assistant.userprofile)

        self.menu_item1 = MenuItem.objects.create(
            service=self.link_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS.STUDENT,
            menu_label="Overriden Label",
            menu_icon_class="star"
        )

        self.menu_item2 = MenuItem.objects.create(
            service=self.link_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS.STUDENT,
            enabled=False
        )

        self.menu_item3 = MenuItem.objects.create(
            service=self.disabled_link_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS.STUDENT
        )

        self.menu_item4 = MenuItem.objects.create(
            service=self.lti_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS.STUDENT
        )

        self.menu_item5 = MenuItem.objects.create(
            service=self.lti_service,
            course_instance=self.course_instance,
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
