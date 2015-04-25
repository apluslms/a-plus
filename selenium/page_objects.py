from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from locators import FirstPageLocators, LoginPageLocators, BasePageLocators, HomePageLocators, CourseLocators, ExercisePageLocators, MyFirstExerciseLocators


class CourseName:
    APLUS = 1
    HOOK = 2


class AbstractPage(object):
    base_url = "http://localhost:8001"

    def __init__(self, driver, base_url=base_url):
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

    def logout(self):
        self.getElement(CourseLocators.LOGOUT_LINK).click()


class LoginPage(AbstractPage):
    defaultUsername = "jenkins"
    defaultPassword = "jenkins"

    def __init__(self, driver):
        AbstractPage.__init__(self, driver)
        self.load("", FirstPageLocators.BANNER)

    def loginToCourse(self, course, username=defaultUsername, password=defaultPassword):
        if (course == CourseName.APLUS):
            self.getElement(CourseLocators.APLUS_TEST_COURSE_INSTANCE_BUTTON).click()
            self.signIn(username, password)
            self.waitForElement(CourseLocators.LOGGED_USER_LINK)
        elif (course == CourseName.HOOK):
            self.getElement(CourseLocators.HOOK_EXAMPLE_BUTTON).click()
            self.signIn(username, password)
            self.waitForElement(CourseLocators.LOGGED_USER_LINK)

    def signIn(self, username, password):
        self.getElement(LoginPageLocators.USERNAME_INPUT).send_keys(username)
        self.getElement(LoginPageLocators.PASSWORD_INPUT).send_keys(password)
        self.getElement(LoginPageLocators.SUBMIT_BUTTON).click()


class BasePage(AbstractPage):
    def __init__(self, driver):
        AbstractPage.__init__(self, driver)

    def clickHomeLink(self):
        self.getElement(BasePageLocators.HOME_LINK).click()

    def clickCalendarFeedLink(self):
        self.getElement(BasePageLocators.CALENDAR_FEED_LINK).click()

    def clickResultsLink(self):
        self.getElement(BasePageLocators.RESULTS_LINK).click()

    def clickUserLink(self):
        self.getElement(BasePageLocators.USER_LINK).click()

    def clickTeachersViewLink(self):
        self.getElement(BasePageLocators.TEACHERS_VIEW_LINK).click()

    def clickAssistantsViewLink(self):
        self.getElement(BasePageLocators.ASSISTANTS_VIEW_LINK).click()

class HomePage(BasePage):
    def __init__(self, driver):
        BasePage.__init__(self, driver)
        self.load("/course/aplus1/basic_instance", HomePageLocators.MAIN_SCORE)

    def getMainScore(self):
        return self.getElement(HomePageLocators.MAIN_SCORE).text;

    def clickFilterCategories(self):
        self.getElement(HomePageLocators.FILTER_CATEGORIES_BUTTON).click()

    def isOnlineExercisesCheckboxSelected(self):
        return self.getElement(HomePageLocators.ONLINE_EXERCISES_CHECKBOX).is_selected()

    def clickOnlineExercisesCheckbox(self):
        self.getElement(HomePageLocators.ONLINE_EXERCISES_CHECKBOX).click()

    def clickUpdateFilters(self):
        self.getElement(HomePageLocators.UPDATE_FILTERS_BUTTON).click()

class ExercisePage(BasePage):
    def __init__(self, driver):
        BasePage.__init__(self, driver)

    def getAllowedSubmissions(self):
        return self.getElement(ExercisePageLocators.ALLOWED_SUBMISSIONS).text

    def getExerciseScore(self):
        return self.getElement(ExercisePageLocators.EXERCISE_SCORE).text

    def getNumberOfSubmitters(self):
        return self.getElement(ExercisePageLocators.NUMBER_OF_SUBMITTERS).text

    def getAverageSubmissionsPerStudent(self):
        return self.getElement(ExercisePageLocators.AVERAGE_SUBMISSIONS_PER_STUDENT).text

class MyFirstExerciseGrader(ExercisePage):
    def __init__(self, driver):
        ExercisePage.__init__(self, driver)
        self.load("/exercise/1/", MyFirstExerciseLocators.MAIN_TITLE)

    def setText(self, text):
        self.getElement(MyFirstExerciseLocators.TEXT_INPUT).send_keys(text)

    def submit(self):
        self.getElement(MyFirstExerciseLocators.SUBMIT_BUTTON).click()


