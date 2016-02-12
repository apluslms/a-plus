import os
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

TEST_PATH = os.path.dirname(os.path.dirname(__file__))
TEST_DB = os.path.join(TEST_PATH, 'aplus.db')
TEST_COPY = os.path.join(TEST_PATH, 'aplus.db_copy')

class TestInitializer(object):

    def getFirefoxDriverWithLoggingEnabled(self):
        firefoxCapabilities =  DesiredCapabilities.FIREFOX
        firefoxCapabilities['loggingPrefs'] = {'Browser': 'ALL'}
        profile = webdriver.FirefoxProfile()
        profile.set_preference('startup.homepage_welcome_url.additional', '')
        firefoxDriver = webdriver.Firefox(profile, capabilities=firefoxCapabilities)
        firefoxDriver.set_window_size(1024, 768)
        return firefoxDriver

    # This just replaces the current database with a copy.
    # We could/should? improve this by dropping all rows and inserting them again.
    def recreateDatabase(self):
        if not os.path.exists(TEST_DB):
            raise Exception('The A+ Django needs to be run with environment variable APLUS_DB_FILE=selenium_test/aplus.db')
        if not os.path.exists(TEST_COPY):
            os.system("cp " + TEST_DB + " " + TEST_COPY)
        os.system("cp " + TEST_COPY + " " + TEST_DB)
