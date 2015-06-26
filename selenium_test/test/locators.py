from selenium.webdriver.common.by import By

class LoginPageLocators(object):
    USERNAME_INPUT = (By.XPATH, "//input[@id='id_username']")
    PASSWORD_INPUT = (By.XPATH, "//input[@id='id_password']")
    SUBMIT_BUTTON = (By.XPATH, "//input[@type='submit']")

class FirstPageLocators(object):
    BANNER = (By.XPATH, "//h1/small[contains(text(), 'the interoperable e-learning platform')]")
    APLUS_TEST_COURSE_INSTANCE_BUTTON = (By.XPATH, "//a[contains(text(),'A+ Test Course Instance')]")
    HOOK_EXAMPLE_BUTTON = (By.XPATH, "//a[contains(text(),'Hook Example')]")

class BasePageLocators(object):
    COURSE_BANNER = (By.XPATH, "//*[@id='main_content']/div[1]/div/div/h1/small")
    HOME_LINK = (By.XPATH, "//*[@id='course-menu']/li[2]/a")
    CALENDAR_FEED_LINK = (By.XPATH, "//*[@id='course-menu']/li/a[contains(@href, '/export-calendar/')]")
    RESULTS_LINK = (By.XPATH, "//*[@id='course-menu']/li/a[contains(@href, '/user/results')]")
    USER_LINK = (By.XPATH, "//*[@id='course-menu']/li/a[contains(@class, 'profile-link')]")
    TEACHERS_VIEW_LINK = (By.XPATH, "//*[@id='course-menu']/li/a[contains(@class, 'teachers-link')]")
    LOGGED_USER_LINK = (By.XPATH, "//*[@id='user-status']//a[contains(text(), 'Logged in as')]")
    LOGOUT_LINK = (By.XPATH, "//*[@id='user-status']//a[contains(@href, '/accounts/logout/')]")
    LOGOUT_BANNER = (By.XPATH, "//div[@class='alert alert-success']")
    WARNING_BANNER = (By.XPATH, "//div[@class='alert alert-warning']")
    NOTIFICATION_MENU = (By.XPATH, "//*[@id='notification-menu']")

class HomePageLocators(object):
    MAIN_SCORE = (By.XPATH, "//div[contains(@class, 'my-score-box')]/h2")
    FILTER_CATEGORIES_BUTTON = (By.XPATH, "//*[@id='schedule-filters-btn']")
    ONLINE_EXERCISES_CHECKBOX = (By.XPATH, "//*[@id='category_filter_1']")
    UPDATE_FILTERS_BUTTON = (By.XPATH, "//input[contains(@value, 'Update filters')]")

class ExercisePageLocators(object):
    MAIN_TITLE = (By.XPATH, "//*[@id='title']")
    EXERCISE_SCORE = (By.XPATH, "//*[@id='exercise-info']/div/h2")
    NUMBER_OF_SUBMITTERS = (By.XPATH, "//*[@id='exercise-info']/dl[2]/dd[1]")
    AVERAGE_SUBMISSIONS_PER_STUDENT = (By.XPATH, "//*[@id='exercise-info']/dl[2]/dd[2]")
    ALLOWED_SUBMISSIONS = (By.XPATH, "//*[@id='exercise-info']/dl[1]/dd")
    MY_SUBMISSIONS_LIST = (By.XPATH, "//*[@id='main_content']/div[2]/div[2]/div[1]/ul/li[2]/ul/li")

class CourseArchiveLocators(object):
    COURSE_ID_TITLE = (By.XPATH, "//*[@id='course1']/h3/small")
    APLUS_LINK = (By.XPATH, "//*[@id='course1']/li/a[contains(@href, '/aplus1/basic_instance/')]")
    HOOK_LINK = (By.XPATH, "//*[@id='course1']/li/a[contains(@href, '/aplus1/hook_instance/')]")

class StaffPageLocators(object):
    SUBMISSION_LINKS = (By.XPATH, "//a[contains(@href,'/submissions/')]")

class TeachersPageLocators(object):
    TEACHERS_VIEW_BANNER = (By.XPATH, "//*[@id='main_content']/div[2]/div[2]/h2[contains(text(), 'Teacher')]")
    EDIT_LEARNING_MODULE_LINKS = (By.XPATH, "//a[contains(@href,'/aplus1/basic_instance/exercises/1/edit/')]")
    REMOVE_LEARNING_MODULE_LINKS = (By.XPATH, "//a[contains(@href,'/aplus1/basic_instance/exercises/1/delete/')]")

class AssistantsPageLocators(object):
    ASSISTANTS_VIEW_BANNER = (By.XPATH, "//*[@id='main_content']/div[2]/div[2]/h2[contains(text(), 'Assistant')]")

class EditModulePageLocators(object):
    EDIT_MODULE_PAGE_BANNER = (By.XPATH, "//*[@id='main_content']/div[2]/div[2]/h2[contains(text(), 'Edit module')]")
    COURSE_NAME_INPUT = (By.XPATH, "//*[@id='id_name']")
    POINTS_TO_PASS_INPUT = (By.XPATH, "//*[@id='id_points_to_pass']")
    OPENING_TIME_INPUT = (By.XPATH, "//*[@id='id_opening_time']")
    CLOSING_TIME_INPUT = (By.XPATH, "//*[@id='id_closing_time']")
    SUBMIT_BUTTON = (By.XPATH, "//form//input[@type='submit']")
    SUCCESSFUL_SAVE_BANNER = (By.XPATH, "//*[@id='main_content']/div[@class='alert alert-success']")

class EditExercisePageLocators(object):
    EDIT_EXERCISE_PAGE_BANNER = (By.XPATH, "//*[@id='main_content']/div[2]/div[2]/h2[contains(text(), 'Edit exercise')]")
    EXERCISE_NAME_INPUT = (By.XPATH, "//*[@id='id_name']")
    MAX_SUBMISSIONS_INPUT = (By.XPATH, "//*[@id='id_max_submissions']")
    MAX_POINTS_INPUT = (By.XPATH, "//*[@id='id_max_points']")
    POINTS_TO_PASS_INPUT = (By.XPATH, "//*[@id='id_points_to_pass']")
    SUBMIT_BUTTON = (By.XPATH, "//form//input[@type='submit']")
    SUCCESSFUL_SAVE_BANNER = (By.XPATH, "//*[@id='main_content']/div[@class='alert alert-success']")

class SubmissionPageLocators(object):
    TABLE_FIRST_HEADER = (By.XPATH, "//*[@id='submission-table']/thead/tr[1]/th[1]")
    INSPECTION_LINKS = (By.XPATH, "//*[@id='submission-table']//a[contains(@href, '/inspect/')]")

class StudentFeedbackPageLocators(object):
    ASSISTANT_FEEDBACK_LABEL = (By.XPATH, "//*[@id='exercise']/h2[text()='Assistant feedback']")
    ASSISTANT_FEEDBACK_TEXT = (By.XPATH, "//*[@id='exercise']")
    FEEDBACK_TEXT = (By.XPATH, "//*[@id='exercise']")

class InspectionPageLocators(object):
    ASSESS_THIS_SUBMISSION_LINK = (By.XPATH, "//*[@id='student-submission']//a[contains(@href, '/aplus1/basic_instance/exercises/1/submissions/7/assess/')]")
    NO_FEEDBACK_BANNER = (By.XPATH, "//div[@class='alert alert-info']")
    SUBMITTERS_TEXT = (By.XPATH, "//*[@id='student-submission']/div/dl[1]/dd")
    GRADE_TEXT = (By.XPATH, "//*[@id='student-submission']/div/dl[4]/dd")
    ASSISTANT_FEEDBACK_TEXT = (By.XPATH, "//*[@id='generated-feedback']/div/h2[1]/following-sibling::text()[1]")
    FEEBACK_TEXT = (By.XPATH, "//*[@id='generated-feedback']/div/h2[1]/following-sibling::text()[2]")

class AssessmentPageLocators(object):
    POINTS_INPUT = (By.XPATH, "//*[@id='id_points']")
    ASSISTANT_FEEDBACK_INPUT = (By.XPATH, "//*[@id='id_assistant_feedback']")
    FEEDBACK_INPUT = (By.XPATH, "//*[@id='id_feedback']")
    SAVE_BUTTON = (By.XPATH, "//*[@id='generated-feedback']//input[@type='submit']")

class MyFirstExerciseLocators(object):
    MAIN_TITLE = (By.XPATH, "//*[@id='title'][contains(text(), 'My first exercise')]")
    TEXT_INPUT = (By.XPATH, "//*[@id='exercise']/form/textarea")
    SUBMIT_BUTTON = (By.XPATH, "//*[@id='exercise']/form/input")

class FileUploadGraderLocators(object):
    MAIN_TITLE = (By.XPATH, "//*[@id='title'][contains(text(), 'Attachment exercise')]")
    BROWSE_BUTTON = (By.XPATH, "//*[@id='file[]_id']")
    SUBMIT_BUTTON = (By.XPATH, "//*[@id='exercise']/form/input")

class MyAjaxExerciseGraderLocators(object):
    MAIN_TITLE = (By.XPATH, "//*[@id='title'][contains(text(), 'My AJAX exercise')]")
    TEXT_INPUT = (By.XPATH, "//*[@id='form']/input[1]")
    SUBMIT_BUTTON = (By.XPATH, "//*[@id='exercise']/form/input[@type='submit']")
