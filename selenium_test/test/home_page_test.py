import unittest

from test_initializer import TestInitializer
from page_objects import LoginPage, HomePage
from locators import BasePageLocators


class HomePageTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()
        TestInitializer().recreateDatabase()
        LoginPage(self.driver).loginAsStudent()

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
        homePage.isElementPresent(BasePageLocators.WARNING_BANNER)

        homePage.clickFilterCategories()
        self.assertTrue(homePage.isOnlineExercisesCheckboxSelected(), 'Online exercises checkbox should have been checked')

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
