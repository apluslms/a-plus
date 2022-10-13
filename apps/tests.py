from django.test import TestCase
from django.test.client import Client

from apps.app_renderers import build_plugin_renderers
from apps.models import HTMLPlugin, ExternalIFramePlugin, RSSPlugin
from course.models import Course, CourseInstance


HTML_PLUGIN_CONTENT = "test_content1245123"
RSS_PLUGIN_ADDRESS = "address12453"
IFRAME_PLUGIN_ADDRESS = "address13123"


class AppsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.course = Course.objects.create(name="Test", code="test", url="test")
        self.instance = CourseInstance.objects.create(course=self.course,
                                                      instance_name="Ins",
                                                      starting_time="2000-01-01T12:00:00.000Z",
                                                      ending_time="2020-01-01T12:00:00.000Z")

        self.html_plugin = HTMLPlugin.objects.create(container=self.instance,
                                                     title="HTML Plugin",
                                                     views="exercise,course_instance",
                                                     content=HTML_PLUGIN_CONTENT)

        self.rss_plugin = RSSPlugin.objects.create(container=self.instance,
                                                   title="RSS Plugin",
                                                   views="course_instance",
                                                   feed_url=RSS_PLUGIN_ADDRESS)

        self.iframe_plugin = ExternalIFramePlugin.objects.create(container=self.instance,
                                                                 title="Iframe Plugin",
                                                                 views="exercise",
                                                                 service_url=IFRAME_PLUGIN_ADDRESS,
                                                                 width=100, height=200)

    def test_plugin_builder_selections(self):
        renderers = build_plugin_renderers(self.instance.plugins, 'submission',
                                           course_instance=self.instance, course=self.course)
        self.assertEqual(len(renderers), 0)
        renderers = build_plugin_renderers(self.instance.plugins, 'exercise',
                                           course_instance=self.instance, course=self.course)
        self.assertEqual(len(renderers), 2)
        renderers = build_plugin_renderers(self.instance.plugins, 'course_instance',
                                           course_instance=self.instance, course=self.course)
        self.assertEqual(len(renderers), 2)

    def test_iframe_plugin(self):
        renderers = build_plugin_renderers(ExternalIFramePlugin.objects, 'exercise',
                                           course_instance=self.instance, course=self.course)
        html = renderers[0].render()
        self.assertTrue(IFRAME_PLUGIN_ADDRESS in html)

    def test_html_plugin(self):
        renderers = build_plugin_renderers(HTMLPlugin.objects, 'exercise',
                                           course_instance=self.instance, course=self.course)
        html = renderers[0].render()
        self.assertTrue(HTML_PLUGIN_CONTENT in html)

    def test_rss_plugin(self):
        renderers = build_plugin_renderers(RSSPlugin.objects, 'course_instance',
                                           course_instance=self.instance, course=self.course)
        html = renderers[0].render() # noqa: unused-variable
        # No real content expected but should not raise errors.
