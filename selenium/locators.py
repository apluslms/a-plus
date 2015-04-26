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
    HOME_LINK = (By.XPATH, "//*[@id='main_content']/div[2]/div[1]/ul/li[2]/a")
    CALENDAR_FEED_LINK = (By.XPATH, "//*[@id='main_content']/div[2]/div[1]/ul/li[3]/a")
    RESULTS_LINK = (By.XPATH, "//*[@id='main_content']/div[2]/div[1]/ul/li[4]/a")
    USER_LINK = (By.XPATH, "//*[@id='main_content']/div[2]/div[1]/ul/li[5]/a")
    TEACHERS_VIEW_LINK = (By.XPATH, "//*[@id='main_content']/div[2]/div[1]/ul/li[7]/a")
    ASSISTANTS_VIEW_LINK = (By.XPATH, "//*[@id='main_content']/div[2]/div[1]/ul/li[8]/a")
    LOGGED_USER_LINK = (By.XPATH, "//*[@id='user-status']/li[2]/a")
    LOGOUT_LINK = (By.XPATH, "//*[@id='user-status']/li[3]/a")
    LOGOUT_BANNER = "//div[@class='alert alert-success']"

class HomePageLocators(object):
    MAIN_SCORE = (By.XPATH, "//*[@id='main_content']/div[2]/div[2]/div/div[2]/div/h2")
    FILTER_CATEGORIES_BUTTON = (By.XPATH, "//*[@id='schedule-filters-btn']")
    ONLINE_EXERCISES_CHECKBOX = (By.XPATH, "//*[@id='category_filter_1']")
    UPDATE_FILTERS_BUTTON = (By.XPATH, "//*[@id='filters-collapse']/div/form/input")

class ExercisePageLocators(object):
    MAIN_TITLE = (By.XPATH, "//*[@id='title']")
    EXERCISE_SCORE = (By.XPATH, "//*[@id='exercise-info']/div/h2")
    NUMBER_OF_SUBMITTERS = (By.XPATH, "//*[@id='exercise-info']/dl[2]/dd[1]")
    AVERAGE_SUBMISSIONS_PER_STUDENT = (By.XPATH, "//*[@id='exercise-info']/dl[2]/dd[2]")
    ALLOWED_SUBMISSIONS = (By.XPATH, "//*[@id='exercise-info']/dl[1]/dd")
    MY_SUBMISSIONS_LIST = (By.XPATH, "//*[@id='main_content']/div[2]/div[2]/div[1]/ul/li[2]/ul/li")

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
    SUBMIT_BUTTON = (By.XPATH, "//*[@id='exercise']/form/input")
