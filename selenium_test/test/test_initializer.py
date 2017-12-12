import os
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

TEST_PATH = os.path.dirname(os.path.dirname(__file__))
TEST_DB = os.path.join(TEST_PATH, 'aplus.db')
TEST_COPY = os.path.join(TEST_PATH, 'aplus.db_copy')

class TestInitializer(object):

    def getDefaultDriver(self):
        driver = self.getFirefoxDriver()
        driver.set_window_size(1024,768)
        return driver

    def setupDisplay(self):
        # Headless with xvfb. Alternatively may just xvfb-run python.
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(1024,768))
        display.start()

    def getChromeDriver(self):
        return webdriver.Chrome()

    def getFirefoxDriver(self):
        return webdriver.Firefox()

    # This just replaces the current database with a copy.
    # TODO Should use Django unit tests that run selenium.
    def recreateDatabase(self):
        if not os.path.exists(TEST_DB):
            raise Exception('The A+ Django needs to be run with environment variable APLUS_DB_FILE=selenium_test/aplus.db')
        if not os.path.exists(TEST_COPY):
            os.system("cp " + TEST_DB + " " + TEST_COPY)
        os.system("cp " + TEST_COPY + " " + TEST_DB)
