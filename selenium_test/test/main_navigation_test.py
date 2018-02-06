import unittest

from test_initializer import TestInitializer
from page_objects import BasePage, LoginPage, CourseName


class MainNavigationTest(unittest.TestCase):
    baseUrl = BasePage.base_url + "/aplus1/basic_instance/"

    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()
        LoginPage(self.driver).loginAsTeacher()

    def testNavigateToResults(self):
        BasePage(self.driver).clickResultsLink()
        self.assertEqual(self.baseUrl + 'user/results/', str(self.driver.current_url))

    #def testNavigateToUserPage(self):
    #    BasePage(self.driver).clickUserLink()
    #    self.assertEqual(self.baseUrl + 'user/notifications/', str(self.driver.current_url))

    def testNavigateToTeachersView(self):
        BasePage(self.driver).clickTeachersViewLink()
        self.assertEqual(self.baseUrl + 'teachers/', str(self.driver.current_url))

    # def testDownloadCalendar(self):
    #    BasePage(self.driver).clickCalendarFeedLink()
    #    self.assertEqual("Download calendar (ics)", str(self.driver.switch_to.active_element.text))

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
