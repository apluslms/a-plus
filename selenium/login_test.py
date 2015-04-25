import unittest
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

from page_objects import CourseName, LoginPage, HomePage
from locators import CourseLocators

class LoginTest(unittest.TestCase):
    logoutPageURI = '/accounts/logout'

    def setUp(self):
        # Set up browser logging
        firefoxCapabilities =  DesiredCapabilities.FIREFOX
        firefoxCapabilities['loggingPrefs'] = {'Browser': 'ALL'}
        self.driver = webdriver.Firefox(capabilities=firefoxCapabilities)

    def testLoginToTestCourseInstance(self):
        loginPage = LoginPage(self.driver)
        loginPage.loginToCourse(CourseName.APLUS)
        assert LoginPage.defaultUsername in loginPage.getElement(CourseLocators.LOGGED_USER_LINK).text
        loginPage.logout()
        assert self.logoutPageURI in self.driver.current_url


    def testLoginToExampleHookCourseInstance(self):
        loginPage = LoginPage(self.driver)
        loginPage.loginToCourse(CourseName.HOOK)
        assert LoginPage.defaultUsername in loginPage.getElement(CourseLocators.LOGGED_USER_LINK).text
        loginPage.logout()
        assert self.logoutPageURI in self.driver.current_url

    def testInitialScoreShouldBeZero(self):
        LoginPage(self.driver).loginToCourse(CourseName.APLUS)
        mainPage = HomePage(self.driver)
        assert "0 / 300" == mainPage.getMainScore().text

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)