from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from course.models import Course, CourseInstance
from userprofile.models import User
from .models import LinkService, LTIService, MenuItem
from .templatetags import external_services as tags


class ExternalServicesTest(TestCase):
    def setUp(self):
        self.user = User(username="testUser")
        self.user.set_password("testPassword")
        self.user.save()

        self.link_service = LinkService.objects.create(
            url="http://www.external-service.com",
            menu_label="External Service"
        )

        self.disabled_link_service = LinkService.objects.create(
            url="http://www.disabled-external-service.com",
            menu_label="Disabled External Service",
            enabled=False
        )
        self.lti_service = LTIService.objects.create(
            url="http://www.lti-service.com",
            menu_label="LTI Service",
            menu_icon_class="star",
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

        self.menu_item1 = MenuItem.objects.create(
            service=self.link_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS_STUDENT,
            menu_label="Overriden Label",
            menu_icon_class="star"
        )

        self.menu_item2 = MenuItem.objects.create(
            service=self.link_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS_STUDENT,
            enabled=False
        )

        self.menu_item3 = MenuItem.objects.create(
            service=self.disabled_link_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS_STUDENT
        )

        self.menu_item4 = MenuItem.objects.create(
            service=self.disabled_link_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS_STUDENT,
            enabled=False
        )

        self.menu_item5 = MenuItem.objects.create(
            service=self.lti_service,
            course_instance=self.course_instance,
            access=MenuItem.ACCESS_STUDENT
        )

    def test_linkservice_string(self):
        self.assertEqual("External Service: http://www.external-service.com", str(self.link_service))
        self.assertEqual("[Disabled] Disabled External Service: http://www.disabled-external-service.com", str(self.disabled_link_service))
        self.assertEqual("LTI Service: http://www.lti-service.com", str(self.lti_service))

    def test_menuitem_label(self):
        self.assertEqual("Overriden Label", self.menu_item1.label)
        self.assertEqual("External Service", self.menu_item2.label)
        self.assertEqual("Disabled External Service", self.menu_item3.label)
        self.assertEqual("Disabled External Service", self.menu_item4.label)
        self.assertEqual("LTI Service", self.menu_item5.label)

    def test_menuitem_icon_class(self):
        self.assertEqual("star", self.menu_item1.icon_class)
        self.assertEqual("globe", self.menu_item2.icon_class)
        self.assertEqual("globe", self.menu_item3.icon_class)
        self.assertEqual("globe", self.menu_item4.icon_class)
        self.assertEqual("star", self.menu_item5.icon_class)

    def test_menuitem_url(self):
        self.assertEqual("http://www.external-service.com", self.menu_item1.url)
        self.assertEqual("http://www.external-service.com", self.menu_item2.url)
        self.assertEqual("http://www.disabled-external-service.com", self.menu_item3.url)
        self.assertEqual("http://www.disabled-external-service.com", self.menu_item4.url)
        self.assertEqual("/Course-Url/T-00.1000_2011/lti-login/5/", self.menu_item5.url)

    def test_menuitem_string(self):
        self.assertEqual("123456 Fall 2011: ", str(self.menu_item1))
        self.assertEqual("[Disabled] 123456 Fall 2011: ", str(self.menu_item2))
        self.assertEqual("[Disabled] 123456 Fall 2011: ", str(self.menu_item3))
        self.assertEqual("[Disabled] 123456 Fall 2011: ", str(self.menu_item4))
        self.assertEqual("123456 Fall 2011: ", str(self.menu_item5))

    def test_view(self):
        url = self.menu_item5.url
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username="testUser", password="testPassword")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("oauth_signature" in str(response.content))

        self.assertEqual(tags.external_menu_entries(self.course_instance.id).count(), 2)
        self.assertEqual(tags.external_staff_menu_entries(self.course_instance.id, True, True).count(), 0)

        self.menu_item5.access = MenuItem.ACCESS_ASSISTANT
        self.menu_item5.save()
        self.assertEqual(tags.external_menu_entries(self.course_instance.id).count(), 1)
        self.assertEqual(tags.external_staff_menu_entries(self.course_instance.id, True, True).count(), 1)
        self.assertEqual(tags.external_staff_menu_entries(self.course_instance.id, True, False).count(), 1)
        self.assertEqual(tags.external_staff_menu_entries(self.course_instance.id, False, False).count(), 0)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.course_instance.assistants.add(self.user.userprofile)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.menu_item5.access = MenuItem.ACCESS_TEACHER
        self.menu_item5.save()
        self.assertEqual(tags.external_menu_entries(self.course_instance.id).count(), 1)
        self.assertEqual(tags.external_staff_menu_entries(self.course_instance.id, True, True).count(), 1)
        self.assertEqual(tags.external_staff_menu_entries(self.course_instance.id, True, False).count(), 0)
        self.assertEqual(tags.external_staff_menu_entries(self.course_instance.id, False, False).count(), 0)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.course.teachers.add(self.user.userprofile)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
