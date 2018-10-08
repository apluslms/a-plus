from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from locators import FirstPageLocators, \
    LoginPageLocators, \
    BasePageLocators, \
    EditModulePageLocators, \
    EditExercisePageLocators, \
    CourseArchiveLocators, \
    HomePageLocators, \
    StaffPageLocators, \
    TeachersPageLocators, \
    SubmissionPageLocators, \
    StudentFeedbackPageLocators, \
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
        self.wait_timeout = 10
        self.condition_wait_timeout = 10

    def load(self, url, loaded_check=None):
        url = self.base_url + url
        self.driver.get(url)
        if loaded_check:
            self.waitForElement(loaded_check)
        # The log command is not supported.
        #self.checkBrowserErrors()

    def openDropdown(self, link, dest, timeout=None):
        self.getElement(link).click()
        self.waitForVisibleElement(dest)

    def clickThrough(self, element, timeout=None):
        try:
            self.clickThroughElement(self.getElement(element), timeout)
        except TimeoutException:
            raise TimeoutException("Link staleness failed after click: {0}".format(element))

    def clickThroughElement(self, link, timeout=None):
        link.click()
        try:
            WebDriverWait(self.driver, timeout or self.wait_timeout).until(EC.staleness_of(link))
        except TimeoutException:
            raise TimeoutException("Link staleness failed after click")

    def waitForElement(self, element, timeout=None):
        try:
            WebDriverWait(self.driver, timeout or self.wait_timeout).until(EC.presence_of_element_located(element))
        except TimeoutException:
            raise TimeoutException("Wait for element failed: {0}".format(element))

    def waitForVisibleElement(self, element):
        try:
            WebDriverWait(self.driver, self.wait_timeout).until(EC.visibility_of_element_located(element))
        except TimeoutException:
            raise TimeoutException("Wait for element visibility failed: {0}".format(element))

    def waitForCondition(self, condition):
        try:
            WebDriverWait(self.driver, self.condition_wait_timeout).until(condition)
        except TimeoutException:
            raise TimeoutException("Wait for condition failed: {0}".format(condition))

    def waitForAjax(self):
        try:
            WebDriverWait(self.driver, self.wait_timeout).until(lambda driver: driver.execute_script("return jQuery.active") == 0)
        except TimeoutException:
            raise TimeoutException("Wait for Ajax timed out.")

    def checkBrowserErrors(self):
        errors = []
        for entry in self.driver.get_log("browser"):
            if (entry['level'] == "ERROR"):
                errors.append(entry['message'])

        if (len(errors) > 0):
            for error in errors:
                print(error)
            raise Exception("Browser errors found")

    def getElement(self, locator):
        return self.driver.find_element(*locator)

    def getElements(self, locator):
        return self.driver.find_elements(*locator)

    def getAlert(self):
        self.waitForCondition(EC.alert_is_present())
        return self.driver.switch_to.alert

    def isElementVisible(self, locator):
        try:
            element = self.getElement(locator)
            return element.is_displayed()
        except NoSuchElementException:
            return False

    def isElementPresent(self, locator):
        try:
            _ = self.getElement(locator)
            return True
        except NoSuchElementException:
            return False

    def clearAndSendKeys(self, locator, text):
        element = self.getElement(locator)
        element.clear()
        element.send_keys(text)

    def getJSON(self):
        import json
        return json.loads(self.driver.find_element_by_tag_name("body").text)


class LoginPage(AbstractPage):
    defaultFullname = "Default User"
    defaultUsername = "user"
    defaultPassword = "admin"
    studentUsername = "student_user"
    assistantUsername = "assistant_user"
    teacherUsername = "teacher_user"

    def __init__(self, driver):
        AbstractPage.__init__(self, driver)
        self.load("", FirstPageLocators.BANNER)

    def loginToCourse(self, course, username=defaultUsername, password=defaultPassword):
        if (course == CourseName.APLUS):
            self.clickThrough(FirstPageLocators.APLUS_TEST_COURSE_INSTANCE_BUTTON)
        elif (course == CourseName.HOOK):
            self.clickThrough(FirstPageLocators.HOOK_EXAMPLE_BUTTON)
        self.waitForElement(LoginPageLocators.BANNER)
        self.waitForElement(BasePageLocators.FOOTER)
        self.signIn(username, password)

    def loginAsStudent(self, course=CourseName.APLUS):
        self.loginToCourse(course, self.studentUsername, self.defaultPassword)

    def loginAsAssistant(self, course=CourseName.APLUS):
        self.loginToCourse(course, self.assistantUsername, self.defaultPassword)

    def loginAsTeacher(self, course=CourseName.APLUS):
        self.loginToCourse(course, self.teacherUsername, self.defaultPassword)

    def signIn(self, username, password):
        self.getElement(LoginPageLocators.USERNAME_INPUT).send_keys(username)
        self.getElement(LoginPageLocators.PASSWORD_INPUT).send_keys(password)
        self.clickThrough(LoginPageLocators.SUBMIT_BUTTON)
        self.waitForElement(BasePageLocators.LOGGED_USER_LINK)
        self.waitForElement(BasePageLocators.FOOTER)


class BasePage(AbstractPage):
    def __init__(self, driver):
        AbstractPage.__init__(self, driver)

    def getCourseBanner(self):
        return str(self.getElement(BasePageLocators.COURSE_BANNER).text)

    def getLoggedInText(self):
        return str(self.getElement(BasePageLocators.LOGGED_USER_LINK).text)

    def waitForPage(self):
        self.waitForElement(BasePageLocators.FOOTER)

    def logout(self):
        self.openDropdown(BasePageLocators.LOGGED_USER_LINK, BasePageLocators.LOGOUT_LINK)
        self.clickThrough(BasePageLocators.LOGOUT_LINK)
        self.waitForPage()

    def clickHomeLink(self):
        self.clickThrough(BasePageLocators.HOME_LINK)
        self.waitForPage()

    def clickCalendarFeedLink(self):
        self.clickThrough(BasePageLocators.CALENDAR_FEED_LINK)
        self.waitForPage()

    def clickResultsLink(self):
        self.clickThrough(BasePageLocators.RESULTS_LINK)
        self.waitForPage()

    def clickUserLink(self):
        self.clickThrough(BasePageLocators.USER_LINK)
        self.waitForPage()

    def clickTeachersViewLink(self):
        self.clickThrough(BasePageLocators.TEACHERS_VIEW_LINK)
        self.waitForPage()

    def hasNewNotifications(self):
        return self.isElementPresent(BasePageLocators.NOTIFICATION_ALERT)


class HomePage(BasePage):
    def __init__(self, driver, course=CourseName.APLUS):
        BasePage.__init__(self, driver)
        if (course == CourseName.APLUS):
            path = "/aplus1/basic_instance"
        elif (course == CourseName.HOOK):
            path = "/aplus1/hook_instance"

        self.load(path, HomePageLocators.MAIN_SCORE)

    def getMainScore(self):
        return str(self.getElement(HomePageLocators.MAIN_SCORE).text);

    def clickFilterCategories(self):
        self.getElement(HomePageLocators.FILTER_CATEGORIES_BUTTON).click()
        self.waitForVisibleElement(HomePageLocators.UPDATE_FILTERS_BUTTON)

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

    def getPoints(self):
        return str(self.getElement(ExercisePageLocators.EXERCISE_SCORE).text).split(" / ", 1)[0]

    def getMaxPoints(self):
        return str(self.getElement(ExercisePageLocators.EXERCISE_SCORE).text).split(" / ", 1)[1]

    def getNumberOfSubmitters(self):
        return str(self.getElement(ExercisePageLocators.NUMBER_OF_SUBMITTERS).text)

    def getAverageSubmissionsPerStudent(self):
        return str(self.getElement(ExercisePageLocators.AVERAGE_SUBMISSIONS_PER_STUDENT).text)

    def getMySubmissionsList(self):
        return self.getElements(ExercisePageLocators.MY_SUBMISSIONS_LIST)

    def dismissWarning(self):
        if self.isElementPresent(ExercisePageLocators.WARNING_DIALOG_BUTTON):
            self.clickThrough(ExercisePageLocators.WARNING_DIALOG_BUTTON)


class StaffPage(BasePage):
    def __init__(self, driver):
        BasePage.__init__(self, driver)

    def getSubmissionLinks(self):
        return self.getElements(StaffPageLocators.SUBMISSION_LINKS)

    def clickSubmissionLink(self, number):
        submissionLinks = self.getSubmissionLinks()
        if(number <= len(submissionLinks)):
            self.clickThroughElement(submissionLinks[number])
            self.waitForPage()
        else:
            raise Exception("Tried to click submission link number " + number + " but there are only " + len(submissionLinks) + " elements.")

class TeachersPage(BasePage):
    def __init__(self, driver):
        BasePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/teachers/", TeachersPageLocators.TEACHERS_VIEW_BANNER)

class EditModulePage(BasePage):
    def __init__(self, driver, moduleNumber):
        BasePage.__init__(self, driver)
        if (moduleNumber):
            self.load("/aplus1/basic_instance/teachers/module/" + str(moduleNumber) + "/", EditModulePageLocators.EDIT_MODULE_PAGE_BANNER)
        else:
            # Create new module
            self.load("/aplus1/basic_instance/teachers/module/add/", EditModulePageLocators.EDIT_MODULE_PAGE_BANNER)

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
        self.clickThrough(EditModulePageLocators.SUBMIT_BUTTON)
        self.waitForElement(TeachersPageLocators.TEACHERS_VIEW_BANNER)
        self.waitForPage()

    def isSuccessfulSave(self):
        return self.isElementVisible(EditModulePageLocators.SUCCESSFUL_SAVE_BANNER)

class EditExercisePage(BasePage):
    def __init__(self, driver, exerciseNumber=1):
        BasePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/teachers/exercise/" + str(exerciseNumber) + "/", EditExercisePageLocators.EDIT_EXERCISE_PAGE_BANNER)

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
        self.clickThrough(EditExercisePageLocators.SUBMIT_BUTTON)
        self.waitForPage()

    def isSuccessfulSave(self):
        return self.isElementVisible(EditExercisePageLocators.SUCCESSFUL_SAVE_BANNER)


class SubmissionPage(BasePage):
    def __init__(self, driver, moduleId="first-exercise-round", exerciseId="1"):
        BasePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/" + str(moduleId) + "/" + str(exerciseId) + "/submissions/", SubmissionPageLocators.SUBMISSIONS_PAGE_BANNER)

    def getInspectionLinks(self):
        return self.getElements(SubmissionPageLocators.INSPECTION_LINKS)

    def getSubmissionCount(self):
        return len(self.getInspectionLinks())

    def clickInspectionLink(self, number):
        inspectionLinks = self.getInspectionLinks()
        if(len(inspectionLinks) >= number):
            self.clickThroughElement(inspectionLinks.get(number))
            self.waitForPage()
        else:
            raise Exception("Tried to click inspection link number " + number + " but there are only " + len(inspectionLinks) + " elements.")

class StudentFeedbackPage(BasePage):
    def __init__(self, driver, moduleId="first-exercise-round", exerciseId="1", submissionNumber=1):
        BasePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/" + str(moduleId) + "/" + str(exerciseId) +"/submissions/" + str(submissionNumber) + "/", StudentFeedbackPageLocators.ASSISTANT_FEEDBACK_LABEL)

    def getAssistantFeedbackText(self):
        return str(self.getElement(StudentFeedbackPageLocators.ASSISTANT_FEEDBACK_TEXT).text).strip()

    def getFeedbackText(self):
        return str(self.getElement(StudentFeedbackPageLocators.FEEDBACK_TEXT).text).strip()

class InspectionPage(BasePage):
    def __init__(self, driver, moduleId="first-exercise-round", exerciseId="1", submissionNumber=1):
        BasePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/" + str(moduleId) + "/" + str(exerciseId) +"/submissions/" + str(submissionNumber) + "/inspect/", InspectionPageLocators.ASSESS_THIS_SUBMISSION_LINK)

    def doesNotHaveFeedback(self):
        return self.isElementVisible(InspectionPageLocators.NO_FEEDBACK_BANNER)

    def clickAssessThisSubmissionLink(self):
        self.clickThrough(InspectionPageLocators.ASSESS_THIS_SUBMISSION_LINK)
        self.waitForPage()

    def getSubmitters(self):
        return str(self.getElement(InspectionPageLocators.SUBMITTERS_TEXT).text)

    def getGrade(self):
        return str(self.getElement(InspectionPageLocators.GRADE_TEXT).text)

class AssessmentPage(BasePage):
    def __init__(self, driver, moduleId="first-exercise-round", exerciseId="1", submissionNumber=1):
        BasePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/" + str(moduleId) + "/" + str(exerciseId) +"/submissions/" + str(submissionNumber) + "/assess/", AssessmentPageLocators.ASSISTANT_FEEDBACK_INPUT)

    def setPoints(self, points):
        self.clearAndSendKeys(AssessmentPageLocators.POINTS_INPUT, points)

    def setAssistantFeedback(self, text):
        self.clearAndSendKeys(AssessmentPageLocators.ASSISTANT_FEEDBACK_INPUT, text)

    def setFeedback(self, text):
        self.clearAndSendKeys(AssessmentPageLocators.FEEDBACK_INPUT, text)

    def submit(self):
        self.clickThrough(AssessmentPageLocators.SAVE_BUTTON)
        self.waitForPage()


class CourseArchivePage(AbstractPage):
    def __init__(self, driver):
        AbstractPage.__init__(self, driver)
        self.load("/archive/", FirstPageLocators.BANNER)


class MyFirstExerciseGrader(ExercisePage):
    def __init__(self, driver):
        ExercisePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/first-exercise-round/1/", MyFirstExerciseLocators.MAIN_TITLE)

    def setText(self, text):
        self.getElement(MyFirstExerciseLocators.TEXT_INPUT).send_keys(text)

    def submit(self):
        self.clickThrough(MyFirstExerciseLocators.SUBMIT_BUTTON)
        self.waitForElement(ExercisePageLocators.RECEIVED_BANNER)
        self.waitForPage()


class FileUploadGrader(ExercisePage):
    def __init__(self, driver):
        ExercisePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/first-exercise-round/2/", FileUploadGraderLocators.MAIN_TITLE)

    def submit(self):
        # Failed to select actual file to submit.
        #script = "document.getElementById('myfile_id').value='/tmp/selenium_test_file';";
        #self.driver.execute_script(script)
        self.clickThrough(FileUploadGraderLocators.SUBMIT_BUTTON)
        self.waitForElement(ExercisePageLocators.RECEIVED_BANNER)
        self.waitForPage()


class MyAjaxExerciseGrader(ExercisePage):
    def __init__(self, driver):
        ExercisePage.__init__(self, driver)
        self.load("/aplus1/basic_instance/first-exercise-round/3/", MyAjaxExerciseGraderLocators.MAIN_TITLE)

    def setText(self, text):
        self.getElement(MyAjaxExerciseGraderLocators.TEXT_INPUT).send_keys(text)

    def submit(self):
        self.getElement(MyAjaxExerciseGraderLocators.SUBMIT_BUTTON).click()
        alert = self.getAlert()
        alert.accept()
        self.waitForAjax()
