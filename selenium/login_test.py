import unittest
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from test_helper import TestHelper
from page_objects import CourseName, LoginPage

class LoginTest(unittest.TestCase):
    logoutPageURI = '/accounts/logout'

    def setUp(self):
       self.driver = TestHelper().getFirefoxDriverWithLoggingEnabled()

    def testLoginToTestCourseInstance(self):
        loginPage = LoginPage(self.driver)
        loginPage.loginToCourse(CourseName.APLUS)
        self.assertTrue(LoginPage.defaultUsername in loginPage.getLoggedInUsername())
        loginPage.logout()
        self.assertTrue(self.logoutPageURI in self.driver.current_url)


    def testLoginToExampleHookCourseInstance(self):
        loginPage = LoginPage(self.driver)
        loginPage.loginToCourse(CourseName.HOOK)
        self.assertTrue(LoginPage.defaultUsername in loginPage.getLoggedInUsername())
        loginPage.logout()
        self.assertTrue(self.logoutPageURI in self.driver.current_url)

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)