from selenium.webdriver.common.by import By

class CommonLocators:
    FORBIDDEN_PAGE = (
        By.XPATH,
        "//div[@class='message'][contains(text(), "
        "'Unfortunately, you are not permitted to view this content')]"
    )
    PERMISSION_DENIED_ACCESS_MODE = (
        By.XPATH,
        "//main[@id='content']//div[@class='message'][contains(text(), "
        "'Unfortunately, you are not permitted to view this content')]"
    )

class LoginPageLocators:
    BANNER = (By.XPATH, "//*[@class='page-header']/h1[contains(text(), 'Log in to A+')]")
    USERNAME_INPUT = (By.XPATH, "//input[@id='id_username']")
    PASSWORD_INPUT = (By.XPATH, "//input[@id='id_password']")
    SUBMIT_BUTTON = (By.XPATH, "//*[@type='submit']")

class FirstPageLocators:
    BANNER = (By.XPATH, "//*[@class='page-header']/h1")
    APLUS_TEST_COURSE_INSTANCE_BUTTON = (
        By.XPATH,
        "//div[contains(@class, 'frontpage card')]//a[contains(@href, "
        "'/aplus1/basic_instance/')]//*[contains(@class, 'card-title')]"
    )
    HOOK_EXAMPLE_BUTTON = (
        By.XPATH,
        "//div[contains(@class, 'frontpage card')]//"
        "a[contains(@href, '/aplus1/hook_instance/')]//*[contains(@class, 'card-title')]"
    )
    SHOW_LOGIN_BUTTON = (By.XPATH, "//*[contains(@class, 'show-extra-login-btn')]")

class BasePageLocators:
    COURSE_BANNER = (By.XPATH, "//nav[contains(@class, 'navbar-header')]//ul/li[contains(@class, 'dropdown')]/a")
    FOOTER = (By.XPATH, "//footer[contains(@class, 'site-footer')]")
    HOME_LINK = (By.XPATH, "//*[contains(@class, 'course-menu')]/ul/li[contains(@class, 'menu-home')]/a")
    CALENDAR_FEED_LINK = (By.XPATH, "//*[contains(@class, 'calendar-view')]/p/a[contains(@href, '/export-calendar/')]")
    RESULTS_LINK = (By.XPATH, "//*[contains(@class, 'course-menu')]/ul/li/a[contains(@class, 'menu-results')]")
    USER_LINK = (By.XPATH, "//*[contains(@class, 'course-menu')]/ul/li[contains(@class, 'menu-notifications')]/a")
    TEACHERS_VIEW_LINK = (
        By.XPATH,
        "//*[contains(@class, 'course-menu')]/ul/li[contains(@class, 'menu-edit-course')]/a"
    )
    LOGGED_USER_LINK = (By.XPATH, "//*[contains(@class, 'user-menu')]/*[contains(@class, 'profile-menu')]/a")
    LOGOUT_LINK = (By.XPATH, "//*[contains(@class, 'user-menu')]//a[contains(@href, '/accounts/logout/')]")
    LOGOUT_BANNER = (By.XPATH, "//div[contains(@class, 'alert alert-success')]")
    WARNING_BANNER = (By.XPATH, "//div[contains(@class, 'alert alert-warning')]")
    NOTIFICATION_ALERT = (
        By.XPATH,
        "//*[contains(@class, 'menu-notification')]//span[contains(@class, 'badge-danger')]"
    )

class HomePageLocators:
    MAIN_SCORE = (By.XPATH, "//div[contains(@class, 'card')]/p/strong[contains(@class, 'h2')]")

class ExercisePageLocators:
    MAIN_TITLE = (By.XPATH, "//*[@id='title']")
    EXERCISE_SCORE = (
        By.XPATH,
        ".//*[@id='exercise-info']/div[contains(@class,'card')]/div/p/strong[contains(@class,'exercise-info-points')]"
    )
    NUMBER_OF_SUBMITTERS = (By.XPATH, "//*[@id='exercise-info']//dl/dd[contains(@class, 'exercise-info-submitters')]")
    ALLOWED_SUBMISSIONS = (By.XPATH, "//*[@id='exercise-info']//dl/dd[contains(@class, 'exercise-info-submissions')]")
    MY_SUBMISSIONS_LIST = (By.XPATH, "//li[contains(@class, 'menu-submission')]/ul[@class='dropdown-menu']/li")
    RECEIVED_BANNER = (By.XPATH, "//*[contains(@class, 'alert')]")
    WARNING_DIALOG_BUTTON = (By.XPATH, "//*[contains(@class, 'exercise-warnings-overlay')]//button")

class CourseArchiveLocators:
    APLUS_LINK = (By.XPATH, "//*[@id='course1']/ul/li/a[contains(@href, '/aplus1/basic_instance/')]")
    HOOK_LINK = (By.XPATH, "//*[@id='course1']/ul/li/a[contains(@href, '/aplus1/hook_instance/')]")

class StaffPageLocators:
    SUBMISSION_LINKS = (By.XPATH, "//a[@href='/aplus1/basic_instance/first-exercise-round/1/submissions/']")

class TeachersPageLocators:
    TEACHERS_VIEW_BANNER = (
        By.XPATH,
        "//ol[@class='breadcrumb']/li[@class='active' and contains(text(), 'Edit course')]"
    )
    EDIT_LEARNING_MODULE_LINKS = (By.XPATH, "//a[contains(@href,'/aplus1/basic_instance/teachers/exercise/1/')]")
    REMOVE_LEARNING_MODULE_LINKS = (
        By.XPATH,
        "//a[contains(@href,'/aplus1/basic_instance/teachers/exercise/1/delete/')]"
    )

class EditModulePageLocators:
    EDIT_MODULE_PAGE_BANNER = (
        By.XPATH,
        "//ol[@class='breadcrumb']/li[@class='active' and contains(text(), 'Edit module')]"
    )
    COURSE_NAME_INPUT = (By.XPATH, "//*[@id='id_name']")
    POINTS_TO_PASS_INPUT = (By.XPATH, "//*[@id='id_points_to_pass']")
    OPENING_TIME_INPUT = (By.XPATH, "//*[@id='id_opening_time']")
    CLOSING_TIME_INPUT = (By.XPATH, "//*[@id='id_closing_time']")
    SUBMIT_BUTTON = (By.XPATH, "//form//*[@type='submit']")
    SUCCESSFUL_SAVE_BANNER = (
        By.XPATH,
        "//div[contains(@class, 'site-messages')]/div[contains(@class, 'alert alert-success')]"
    )

class EditExercisePageLocators:
    EDIT_EXERCISE_PAGE_BANNER = (
        By.XPATH,
        "//ol[@class='breadcrumb']/li[@class='active' and contains(text(), 'Edit learning object')]"
    )
    EXERCISE_NAME_INPUT = (By.XPATH, "//*[@id='id_name']")
    MAX_SUBMISSIONS_INPUT = (By.XPATH, "//*[@id='id_max_submissions']")
    MAX_POINTS_INPUT = (By.XPATH, "//*[@id='id_max_points']")
    POINTS_TO_PASS_INPUT = (By.XPATH, "//*[@id='id_points_to_pass']")
    SUBMIT_BUTTON = (By.XPATH, "//form//*[@type='submit']")
    SUCCESSFUL_SAVE_BANNER = (
        By.XPATH,
        "//div[contains(@class, 'site-messages')]/div[contains(@class, 'alert alert-success')]"
    )

class SubmissionPageLocators:
    SUBMISSIONS_PAGE_BANNER = (
        By.XPATH,
        "//ol[@class='breadcrumb']/li[@class='active' and contains(text(), 'All submissions')]"
    )
    INSPECTION_LINKS = (By.XPATH, "//table//a[contains(@href, '/inspect/')]")

class StudentFeedbackPageLocators:
    ASSISTANT_FEEDBACK_LABEL = (By.XPATH, "//h4[text()='Staff feedback']")
    ASSISTANT_FEEDBACK_TEXT = (By.XPATH, "//blockquote")
    FEEDBACK_TEXT = (By.XPATH, "//*[@id='exercise']")

class InspectionPageLocators:
    ASSESSMENT_BUTTON = (
        By.XPATH,
        "//div[contains(@class, 'assessment-panel')]//button[contains(text(), 'Assess manually')]"
    )
    ASSISTANT_FEEDBACK_TOGGLE = (
        By.XPATH,
        "//form[contains(@class, 'assessment-bar')]//button[contains(text(), 'Assistant feedback')]"
    )
    GRADER_FEEDBACK_TOGGLE = (
        By.XPATH,
        "//form[contains(@class, 'assessment-bar')]//button[contains(text(), 'Grader feedback')]"
    )
    POINTS_INPUT = (By.XPATH, "//*[@id='id_points']")
    ASSISTANT_FEEDBACK_INPUT = (By.XPATH, "//*[@id='id_assistant_feedback']")
    FEEDBACK_INPUT = (By.XPATH, "//*[@id='id_feedback']")
    SAVE_BUTTON = (By.XPATH, "//form[contains(@class, 'assessment-bar')]//*[@type='submit']")

class MyFirstExerciseLocators:
    MAIN_TITLE = (By.XPATH, "//*[@id='title'][contains(text(), 'My first exercise')]")
    TEXT_INPUT = (By.XPATH, "//*[@id='exercise-page-content']//form//textarea")
    SUBMIT_BUTTON = (By.XPATH, "//*[@id='exercise-page-content']//form//input[@type='submit']")

class FileUploadGraderLocators:
    MAIN_TITLE = (By.XPATH, "//*[@id='title'][contains(text(), 'File exercise')]")
    BROWSE_BUTTON = (By.XPATH, "//*[@id='myfile_id']")
    SUBMIT_BUTTON = (By.XPATH, "//*[@id='exercise-page-content']//form//input[@type='submit']")

class MyAjaxExerciseGraderLocators:
    MAIN_TITLE = (By.XPATH, "//*[@id='title'][contains(text(), 'My AJAX exercise')]")
    TEXT_INPUT = (By.XPATH, "//*[@id='form']//input[@type='number']")
    SUBMIT_BUTTON = (By.XPATH, "//*[@id='form']//input[@type='submit']")
