from xmlrunner.extra.djangotestrunner import XMLTestRunner
from django.conf import settings
TEST_EXCLUDE_APPS = getattr(settings, 'TEST_EXCLUDE_APPS', [])

class ExcludeAppsXMLTestRunner(XMLTestRunner):

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = super(XMLTestRunner, self).build_suite(test_labels, extra_tests=None, **kwargs)
        if not test_labels:
            tests = []
            for test in suite:
                for app in TEST_EXCLUDE_APPS:
                    if test.__class__.__module__.startswith(app):
                        break
                else:
                    tests.append(test)
            suite._tests = tests
        return suite