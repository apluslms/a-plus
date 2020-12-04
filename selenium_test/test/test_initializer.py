import os
import enum
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

TEST_PATH = os.path.dirname(os.path.dirname(__file__))
TEST_DB = os.path.join(TEST_PATH, 'aplus.db')
TEST_COPY = os.path.join(TEST_PATH, 'aplus.db_copy')

class Browser(enum.Enum):
   firefox = "Firefox"
   chrome = "Chrome"

class TestInitializer(object):

    def getDefaultDriver(self, headless=False, browser="Firefox"):
        driver = self.getDriver(headless, browser)
        driver.set_window_size(1024,768)
        return driver

    def setupDisplay(self):
        # Headless with xvfb. Alternatively may just xvfb-run python.
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(1024,768))
        display.start()

    def getDriver(self, headless=False, browser="Firefox"):
        print('Browser: ' + browser)

        if Browser.firefox.value == browser:
            browser_opts = webdriver.firefox.options.Options
            options = self.setHeadless(browser_opts, headless)
            driver = webdriver.Firefox(options=options)

        elif Browser.chrome.value == browser:
            browser_opts = webdriver.chrome.options.Options
            options = self.setHeadlessChrome(browser_opts, headless)
            driver = webdriver.Chrome(chrome_options=options)

        return driver

    def setHeadless(self, browser_opts, headless):
        options = browser_opts()
        options.headless = headless
        return options

    # This just replaces the current database with a copy.
    # TODO Should use Django unit tests that run selenium.
    def recreateDatabase(self):
        if not os.path.exists(TEST_DB):
            raise Exception('The A+ Django needs to be run with environment variable APLUS_DB_FILE=selenium_test/aplus.db')
        if not os.path.exists(TEST_COPY):
            os.system("cp " + TEST_DB + " " + TEST_COPY)
        os.system("cp " + TEST_COPY + " " + TEST_DB)
