from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from locators import LoginPageLocators, MainPageLocators, CourseLocators

class BasePage(object):
    def __init__(self, driver, base_url="http://localhost:8000"):
        self.driver = driver
        self.base_url = base_url
        self.wait_timeout = 2

    def load(self, url, loaded_check):
        url = self.base_url + url
        self.driver.get(url)
        self.waitForElement(loaded_check)
        self.checkBrowserErrors()

    def waitForElement(self, element):
        try:
            WebDriverWait(self.driver, self.wait_timeout).until(EC.presence_of_element_located(element))
        except TimeoutException:
            print "Wait for element failed: " + str(element)
            raise

    def checkBrowserErrors(self):
        errors = []
        for entry in self.driver.get_log("browser"):
            if (entry[u'level'] == "ERROR"):
                errors.append(entry[u'message'])

        if (len(errors) > 0):
            for error in errors:
                print error
            raise Exception("Browser errors found")

    def getElement(self, locator):
        return self.driver.find_element(*locator)

class LoginPage(BasePage):
    def __init__(self, driver):
        BasePage.__init__(self, driver)
        self.load("", MainPageLocators.BANNER)

    def login_to_course(self, course, username, password):
        if (course == "APLUS"):
            self.getElement(CourseLocators.APLUS_TEST_COURSE_INSTANCE_BUTTON).click()
            self.signIn(username, password)
            self.waitForElement(CourseLocators.APLUS_TEST_COURSE_INSTANCE_BANNER)
        elif (course == "HOOK"):
            self.getElement(CourseLocators.HOOK_EXAMPLE_BUTTON).click()
            self.signIn(username,password)
            self.waitForElement(CourseLocators.HOOK_EXAMPLE_BANNER)

    def signIn(self, username, password):
        self.getElement(LoginPageLocators.USERNAME_INPUT).send_keys(username)
        self.getElement(LoginPageLocators.PASSWORD_INPUT).send_keys(password)
        self.getElement(LoginPageLocators.SUBMIT_BUTTON).click()
