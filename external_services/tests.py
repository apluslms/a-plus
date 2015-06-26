from datetime import datetime, timedelta

from django.test import TestCase

from course.models import Course, CourseInstance
from external_services.models import LinkService, LTIService, MenuItem


class ExternalServicesTest(TestCase):
    def setUp(self):
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
            menu_icon_class="icon-star",
            consumer_key="123456789",
            consumer_secret="987654321"
        )

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        self.today = datetime.now()
        self.tomorrow = self.today + timedelta(days=1)

        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011",
            website="http://www.example.com",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_2011"
        )

        self.menu_item1 = MenuItem.objects.create(
            service=self.link_service,
            course_instance=self.course_instance,
            menu_label="Overriden Label",
            menu_icon_class="icon-star",

        )

        self.menu_item2 = MenuItem.objects.create(
            service=self.link_service,
            course_instance=self.course_instance,
            enabled=False
        )

        self.menu_item3 = MenuItem.objects.create(
            service=self.disabled_link_service,
            course_instance=self.course_instance
        )

        self.menu_item4 = MenuItem.objects.create(
            service=self.disabled_link_service,
            course_instance=self.course_instance,
            enabled=False
        )

        self.menu_item5 = MenuItem.objects.create(
            service=self.lti_service,
            course_instance=self.course_instance
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
        self.assertEqual("icon-star", self.menu_item1.icon_class)
        self.assertEqual("icon-globe", self.menu_item2.icon_class)
        self.assertEqual("icon-globe", self.menu_item3.icon_class)
        self.assertEqual("icon-globe", self.menu_item4.icon_class)
        self.assertEqual("icon-star", self.menu_item5.icon_class)

    def test_menuitem_url(self):
        self.assertEqual("http://www.external-service.com", self.menu_item1.url)
        self.assertEqual("http://www.external-service.com", self.menu_item2.url)
        self.assertEqual("http://www.disabled-external-service.com", self.menu_item3.url)
        self.assertEqual("http://www.disabled-external-service.com", self.menu_item4.url)
        self.assertEqual("/external/lti/5", self.menu_item5.url)

    def test_menuitem_string(self):
        self.assertEqual("123456 Fall 2011: ", str(self.menu_item1))
        self.assertEqual("[Disabled] 123456 Fall 2011: ", str(self.menu_item2))
        self.assertEqual("[Disabled] 123456 Fall 2011: ", str(self.menu_item3))
        self.assertEqual("[Disabled] 123456 Fall 2011: ", str(self.menu_item4))
        self.assertEqual("123456 Fall 2011: ", str(self.menu_item5))
