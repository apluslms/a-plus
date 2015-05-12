import unittest

from .test_initializer import TestInitializer
from selenium_test.page_objects.page_objects import TeachersPage, AssistantsPage, LoginPage, CourseName


class StaffPageTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()
        LoginPage(self.driver).loginToCourse(CourseName.APLUS)

    def testShouldOpenAllTeachersViewSubmissionPages(self):
        linkCount = len(TeachersPage(self.driver).getSubmissionLinks())

        for x in range(0, linkCount):
            teachersPage = TeachersPage(self.driver)
            teachersPage.clickSubmissionLink(x)
            self.assertTrue('/exercise/submissions/list/' + str(x + 1) + "/" in str(self.driver.current_url))

    def testShouldOpenAllAssistantsViewSubmissionPages(self):
        linkCount = len(AssistantsPage(self.driver).getSubmissionLinks())

        for x in range(0, linkCount):
            assistantsPage = AssistantsPage(self.driver)
            assistantsPage.clickSubmissionLink(x)
            self.assertTrue('/exercise/submissions/list/' + str(x + 1) + "/" in str(self.driver.current_url))


    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)