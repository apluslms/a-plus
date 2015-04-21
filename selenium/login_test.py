import unittest
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

from page_objects import LoginPage
from locators import CourseLocators

class LoginTest(unittest.TestCase):
    username = "root"
    password = "maesh3Reem"

    def setUp(self):
        # Set up browser logging
        firefoxCapabilities =  DesiredCapabilities.FIREFOX
        firefoxCapabilities['loggingPrefs'] = {'Browser': 'ALL'}
        self.driver = webdriver.Firefox(capabilities=firefoxCapabilities)

    def testLoginToTestCourseInstance(self):
        login_page = LoginPage(self.driver)
        login_page.login_to_course("APLUS", self.username, self.password)
        assert self.username in login_page.getElement(CourseLocators.LOGGED_USER_LINK).text
        login_page.logout()
        assert "/accounts/logout/" in self.driver.current_url


    def testLoginToExampleHookCourseInstance(self):
        login_page = LoginPage(self.driver)
        login_page.login_to_course("HOOK", self.username, self.password)
        assert self.username in login_page.getElement(CourseLocators.LOGGED_USER_LINK).text
        login_page.logout()
        assert "/accounts/logout/" in self.driver.current_url

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)