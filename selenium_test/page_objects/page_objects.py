from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium_test.locators.locators import FirstPageLocators, \
    LoginPageLocators, \
    BasePageLocators, \
    EditModulePageLocators, \
    EditExercisePageLocators, \
    CourseArchiveLocators, \
    HomePageLocators, \
    StaffPageLocators, \
    TeachersPageLocators, \
    AssistantsPageLocators, \
    SubmissionPageLocators, \
    ExercisePageLocators, \
    InspectionPageLocators, \
    AssessmentPageLocators, \
    MyFirstExerciseLocators, \
    FileUploadGraderLocators, \
    MyAjaxExerciseGraderLocators


class CourseName:
    APLUS = 1
    HOOK = 2

class AbstractPage(object):
    base_url = "http://localhost:8001"

    def __init__(self, driver, base_url=base_url):
        self.driver = driver
        self.base_url = base_url
        self.wait_timeout = 3
        self.condition_wait_timeout = 10

    def load(self, url, loaded_check):
        url = self.base_url + url
        self.driver.get(url)
        self.waitForElement(loaded_check)
        self.checkBrowserErrors()

    def waitForElement(self, element):
        try:
            WebDriverWait(self.driver, self.wait_timeout).until(EC.presence_of_element_located(element))
        except TimeoutException:
            raise("Wait for element failed: " + str(element))

    def waitForCondition(self, condition):
        try:
            WebDriverWait(self.driver, self.condition_wait_timeout).until(condition)
        except TimeoutException:
            raise("Wait for condition failed: " + str(condition))

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

    def getElements(self, locator):
        return self.driver.find_elements(*locator)

    def getAlert(self):
        self.waitForCondition(EC.alert_is_present())
        return self.driver.switch_to_alert()

    def isElementVisible(self, locator):
        try:
            element = self.getElement(locator)
            return element.is_displayed()
        except NoSuchElementException:
            return False

    def clearAndSendKeys(self, locator, text):
        element = self.getElement(locator)
        element.clear()
        element.send_keys(text)


class LoginPage(AbstractPage):
    defaultUsername = "jenkins"
    defaultPassword = "admin"

    def __init__(self, driver):
        AbstractPage.__init__(self, driver)
        self.load("", FirstPageLocators.BANNER)

    def loginToCourse(self, course, username=defaultUsername, password=defaultPassword):
        if (course == CourseName.APLUS):
            self.getElement(FirstPageLocators.APLUS_TEST_COURSE_INSTANCE_BUTTON).click()
            self.signIn(username, password)
            self.waitForElement(BasePageLocators.LOGGED_USER_LINK)
        elif (course == CourseName.HOOK):
            self.getElement(FirstPageLocators.HOOK_EXAMPLE_BUTTON).click()
            self.signIn(username, password)
            self.waitForElement(BasePageLocators.LOGGED_USER_LINK)

    def signIn(self, username, password):
        self.getElement(LoginPageLocators.USERNAME_INPUT).send_keys(username)
        self.getElement(LoginPageLocators.PASSWORD_INPUT).send_keys(password)
        self.getElement(LoginPageLocators.SUBMIT_BUTTON).click()


class BasePage(AbstractPage):
    def __init__(self, driver):
        AbstractPage.__init__(self, driver)

    def getCourseBanner(self):
        return str(self.getElement(BasePageLocators.COURSE_BANNER).text)

    def getLoggedInText(self):
        return str(self.getElement(BasePageLocators.LOGGED_USER_LINK).text)

    def logout(self):
        self.getElement(BasePageLocators.LOGOUT_LINK).click()

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
    def __init__(self, driver, course=CourseName.APLUS):
        BasePage.__init__(self, driver)
        if (course == CourseName.APLUS):
            path = "/course/aplus1/basic_instance"
        elif (course == CourseName.HOOK):
            path = "/course/aplus1/hook_instance"

        self.load(path, HomePageLocators.MAIN_SCORE)

    def getMainScore(self):
        return str(self.getElement(HomePageLocators.MAIN_SCORE).text);

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
        return str(self.getElement(ExercisePageLocators.ALLOWED_SUBMISSIONS).text)

    def getExerciseScore(self):
        return str(self.getElement(ExercisePageLocators.EXERCISE_SCORE).text)

    def getNumberOfSubmitters(self):
        return str(self.getElement(ExercisePageLocators.NUMBER_OF_SUBMITTERS).text)

    def getAverageSubmissionsPerStudent(self):
        return str(self.getElement(ExercisePageLocators.AVERAGE_SUBMISSIONS_PER_STUDENT).text)

    def getMySubmissionsList(self):
        return self.getElements(ExercisePageLocators.MY_SUBMISSIONS_LIST)


class StaffPage(BasePage):
    def __init__(self, driver):
        BasePage.__init__(self, driver)

    def getSubmissionLinks(self):
        return self.getElements(StaffPageLocators.SUBMISSION_LINKS)

    def clickSubmissionLink(self, number):
        submissionLinks = self.getSubmissionLinks()
        if(number <= len(submissionLinks)):
            submissionLinks[number].click()
        else:
            raise Exception("Tried to click submission link number " + number + "but there are only " + len(submissionLinks) + " elements.")

class TeachersPage(StaffPage):
    def __init__(self, driver):
        StaffPage.__init__(self, driver)
        self.load("/course/aplus1/basic_instance/teachers/", TeachersPageLocators.TEACHERS_VIEW_BANNER)

class AssistantsPage(StaffPage):
    def __init__(self, driver):
        StaffPage.__init__(self, driver)
        self.load("/course/aplus1/basic_instance/assistants/", AssistantsPageLocators.ASSISTANTS_VIEW_BANNER)

class EditModulePage(BasePage):
    def __init__(self, driver, moduleNumber):
        BasePage.__init__(self, driver)
        if (moduleNumber):
            self.load("/course/aplus1/basic_instance/modules/" + str(moduleNumber) + "/", EditModulePageLocators.EDIT_MODULE_PAGE_BANNER)
        else:
            # Create new module
            self.load("/course/aplus1/basic_instance/modules/", EditModulePageLocators.EDIT_MODULE_PAGE_BANNER)

    def getCourseName(self):
        return str(self.getElement(EditModulePageLocators.COURSE_NAME_INPUT).get_attribute('value'))

    def getPointsToPass(self):
        return str(self.getElement(EditModulePageLocators.POINTS_TO_PASS_INPUT).get_attribute('value'))

    def getOpeningTime(self):
        return str(self.getElement(EditModulePageLocators.OPENING_TIME_INPUT).get_attribute('value'))

    def getClosingTime(self):
        return str(self.getElement(EditModulePageLocators.CLOSING_TIME_INPUT).get_attribute('value'))

    def setCourseName(self, text):
        self.clearAndSendKeys(EditModulePageLocators.COURSE_NAME_INPUT, text)

    def setPointsToPass(self, points):
        self.clearAndSendKeys(EditModulePageLocators.POINTS_TO_PASS_INPUT, points)

    def setOpeningTime(self, timestamp):
        self.clearAndSendKeys(EditModulePageLocators.OPENING_TIME_INPUT, timestamp)

    def setClosingTime(self, timestamp):
        self.clearAndSendKeys(EditModulePageLocators.CLOSING_TIME_INPUT, timestamp)

    def submit(self):
        self.getElement(EditModulePageLocators.SUBMIT_BUTTON).click()

    def isSuccessfulSave(self):
        return self.isElementVisible(EditModulePageLocators.SUCCESSFUL_SAVE_BANNER)

class EditExercisePage(BasePage):
    def __init__(self, driver, moduleNumber=1, exerciseNumber=1):
        BasePage.__init__(self, driver)
        self.load("/exercise/manage/" + str(moduleNumber) + "/" + str(exerciseNumber) + "/", EditExercisePageLocators.EDIT_EXERCISE_PAGE_BANNER)

    def getExerciseName(self):
        return str(self.getElement(EditExercisePageLocators.EXERCISE_NAME_INPUT).get_attribute('value'))

    def getMaxSubmissions(self):
        return str(self.getElement(EditExercisePageLocators.MAX_SUBMISSIONS_INPUT).get_attribute('value'))

    def getMaxPoints(self):
        return str(self.getElement(EditExercisePageLocators.MAX_POINTS_INPUT).get_attribute('value'))

    def getPointsToPass(self):
        return str(self.getElement(EditExercisePageLocators.POINTS_TO_PASS_INPUT).get_attribute('value'))

    def setExerciseName(self, text):
        self.clearAndSendKeys(EditExercisePageLocators.EXERCISE_NAME_INPUT, text)

    def setMaxSubmissions(self, points):
        self.clearAndSendKeys(EditExercisePageLocators.MAX_SUBMISSIONS_INPUT, points)

    def setMaxPoints(self, timestamp):
        self.clearAndSendKeys(EditExercisePageLocators.MAX_POINTS_INPUT, timestamp)

    def setPointsToPass(self, timestamp):
        self.clearAndSendKeys(EditExercisePageLocators.POINTS_TO_PASS_INPUT, timestamp)

    def submit(self):
        self.getElement(EditExercisePageLocators.SUBMIT_BUTTON).click()

    def isSuccessfulSave(self):
        return self.isElementVisible(EditExercisePageLocators.SUCCESSFUL_SAVE_BANNER)


class SubmissionPage(BasePage):
    def __init__(self, driver, moduleNumber=1):
        BasePage.__init__(self, driver)
        self.load("/exercise/submissions/list/" + str(moduleNumber) + "/", SubmissionPageLocators.TABLE_FIRST_HEADER)

    def getInspectionLinks(self):
        return self.getElements(SubmissionPageLocators.INSPECTION_LINKS)

    def getSubmissionCount(self):
        return len(self.getInspectionLinks())

    def clickInspectionLink(self, number):
        inspectionLinks = self.getInspectionLinks()
        if(len(inspectionLinks) >= number):
            inspectionLinks.get(number).click()
        else:
            raise Exception("Tried to click inspection link number " + number + "but there are only " + len(inspectionLinks) + " elements.")

class InspectionPage(BasePage):
    def __init__(self, driver, submissionNumber=1):
        BasePage.__init__(self, driver)
        self.load("/exercise/submissions/inspect/" + str(submissionNumber) + "/", InspectionPageLocators.ASSESS_THIS_SUBMISSION_LINK)

    def doesNotHaveFeedback(self):
        return self.isElementVisible(InspectionPageLocators.NO_FEEDBACK_BANNER)

    def clickAssessThisSubmissionLink(self):
        self.getElement(InspectionPageLocators.ASSESS_THIS_SUBMISSION_LINK).click()

    def getSubmitters(self):
        return str(self.getElement(InspectionPageLocators.SUBMITTERS_TEXT).text)

    def getGrade(self):
        return str(self.getElement(InspectionPageLocators.GRADE_TEXT).text)

class AssessmentPage(BasePage):
    def __init__(self, driver, submissionNumber=1):
        BasePage.__init__(self, driver)
        self.load("/exercise/submissions/assess/" + str(submissionNumber) + "/", AssessmentPageLocators.ASSISTANT_FEEDBACK_INPUT)

    def setPoints(self):
        self.clearAndSendKeys(AssessmentPageLocators.POINTS_INPUT)

    def setAssistantFeedback(self):
        self.clearAndSendKeys(AssessmentPageLocators.ASSISTANT_FEEDBACK_INPUT)

    def setFeedback(self):
        self.clearAndSendKeys(AssessmentPageLocators.FEEDBACK_INPUT)

    def submit(self):
        self.getElement(AssessmentPageLocators.SAVE_BUTTON).click()


class CourseArchivePage(AbstractPage):
    def __init__(self, driver):
        AbstractPage.__init__(self, driver)
        self.load("/course/archive/", CourseArchiveLocators.COURSE_ID_TITLE)


class MyFirstExerciseGrader(ExercisePage):
    def __init__(self, driver):
        ExercisePage.__init__(self, driver)
        self.load("/exercise/1/", MyFirstExerciseLocators.MAIN_TITLE)

    def setText(self, text):
        self.getElement(MyFirstExerciseLocators.TEXT_INPUT).send_keys(text)

    def submit(self):
        self.getElement(MyFirstExerciseLocators.SUBMIT_BUTTON).click()


class FileUploadGrader(ExercisePage):
    def __init__(self, driver):
        ExercisePage.__init__(self, driver)
        self.load("/exercise/2/", FileUploadGraderLocators.MAIN_TITLE)

    def submit(self):
        self.getElement(FileUploadGraderLocators.SUBMIT_BUTTON).click()


class MyAjaxExerciseGrader(ExercisePage):
    def __init__(self, driver):
        ExercisePage.__init__(self, driver)
        self.load("/exercise/3/", MyAjaxExerciseGraderLocators.MAIN_TITLE)

    def setText(self, text):
        self.getElement(MyAjaxExerciseGraderLocators.TEXT_INPUT).send_keys(text)

    def submit(self):
        self.getElement(MyAjaxExerciseGraderLocators.SUBMIT_BUTTON).click()
        alert = self.getAlert()
        alert.accept()

