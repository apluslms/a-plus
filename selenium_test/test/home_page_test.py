import unittest

from .test_initializer import TestInitializer
from selenium_test.page_objects.page_objects import CourseName, LoginPage, HomePage


class HomePageTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()
        TestInitializer().recreateDatabase()
        LoginPage(self.driver).loginToCourse(CourseName.APLUS)

    def testInitialScoreShouldBeZero(self):
        self.assertEqual("0 / 300", HomePage(self.driver).getMainScore())

    def testFilterCategories(self):
        homePage = HomePage(self.driver)

        homePage.clickFilterCategories()
        self.assertTrue(homePage.isOnlineExercisesCheckboxSelected(), 'Online exercises checkbox should have been checked')

        homePage.clickUpdateFilters()
        homePage.clickFilterCategories()
        self.assertTrue(homePage.isOnlineExercisesCheckboxSelected(), 'Online exercises checkbox should have been checked')

        homePage.clickOnlineExercisesCheckbox()
        homePage.clickUpdateFilters()
        self.assertEqual(HomePage.base_url + '/course/aplus1/basic_instance/set_schedule_filters/?next=/course/aplus1/basic_instance/', str(self.driver.current_url))

        homePage = HomePage(self.driver)
        homePage.clickFilterCategories()
        self.assertTrue(homePage.isOnlineExercisesCheckboxSelected(), 'Online exercises checkbox should have been checked')

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)