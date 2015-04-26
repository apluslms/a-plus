import os
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

class TestHelper(object):
    def getFirefoxDriverWithLoggingEnabled(self):
        # Set up browser logging
        firefoxCapabilities =  DesiredCapabilities.FIREFOX
        firefoxCapabilities['loggingPrefs'] = {'Browser': 'ALL'}
        return webdriver.Firefox(capabilities=firefoxCapabilities)

    def recreateDatabase(self):
        os.system('cp ../aplus.db_copy ../aplus.db')

