from xmlrunner.extra.djangotestrunner import XMLTestRunner
from django.conf import settings

TEST_EXCLUDE_APPS = getattr(settings, 'TEST_EXCLUDE_APPS', [])

class ExcludeAppsXMLTestRunner(XMLTestRunner):

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        if not test_labels:
            test_labels = [app for app in settings.INSTALLED_APPS if not app in TEST_EXCLUDE_APPS]
        return super(ExcludeAppsXMLTestRunner, self).run_tests(test_labels, extra_tests, **kwargs)