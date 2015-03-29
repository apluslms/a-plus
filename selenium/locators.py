from selenium.webdriver.common.by import By

class CourseLocators(object):
    APLUS_TEST_COURSE_INSTANCE_BUTTON = (By.XPATH, "//a[contains(text(),'A+ Test Course Instance')]")
    APLUS_TEST_COURSE_INSTANCE_BANNER = (By.XPATH, "//h1/small[contains(text(), 'A+ Test Course Instance')]")
    HOOK_EXAMPLE_BUTTON = (By.XPATH, "//a[contains(text(),'Hook Example')]")
    HOOK_EXAMPLE_BANNER = (By.XPATH, "//h1/small[contains(text(), 'Hook Example')]")

class LoginPageLocators(object):
    USERNAME_INPUT = (By.XPATH, "//input[@id='id_username']")
    PASSWORD_INPUT = (By.XPATH, "//input[@id='id_password']")
    SUBMIT_BUTTON = (By.XPATH, "//input[@type='submit']")

class MainPageLocators(object):
    BANNER = (By.XPATH, "//h1/small[contains(text(), 'the interoperable e-learning platform')]")
