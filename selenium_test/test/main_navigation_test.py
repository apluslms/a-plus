import unittest

from test_initializer import TestInitializer
from page_objects import BasePage, LoginPage, CourseName


class MainNavigationTest(unittest.TestCase):
    baseUrl = BasePage.base_url + "/course/aplus1/basic_instance/"

    def setUp(self):
        self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()
        LoginPage(self.driver).loginToCourse(CourseName.APLUS)

    def testNavigateToResults(self):
        BasePage(self.driver).clickResultsLink()
        self.assertEqual(self.baseUrl + 'results/', str(self.driver.current_url))

    def testNavigateToUserPage(self):
        BasePage(self.driver).clickUserLink()
        self.assertEqual(self.baseUrl + 'me/', str(self.driver.current_url))

    def testNavigateToTeachersView(self):
        BasePage(self.driver).clickTeachersViewLink()
        self.assertEqual(self.baseUrl + 'teachers/', str(self.driver.current_url))

    def testNavigateToAssistantsView(self):
        BasePage(self.driver).clickAssistantsViewLink()
        self.assertEqual(self.baseUrl + 'assistants/', str(self.driver.current_url))

    def testDownloadCalendar(self):
        BasePage(self.driver).clickCalendarFeedLink()
        self.assertEqual("Calendar feed (ics)", str(self.driver.switch_to.active_element.text))

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
