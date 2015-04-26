import os
import ConfigParser
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

class TestInitializer(object):
    def getFirefoxDriverWithLoggingEnabled(self):
        firefoxCapabilities =  DesiredCapabilities.FIREFOX
        firefoxCapabilities['loggingPrefs'] = {'Browser': 'ALL'}
        return webdriver.Firefox(capabilities=firefoxCapabilities)

    def recreateDatabase(self):
        if('APLUS_HOME' not in os.environ):
            APLUS_HOME = self.getLocalConfigHomePath()
        else:
            APLUS_HOME = os.environ['APLUS_HOME']

        if(not APLUS_HOME):
            print "Test environment is not properly configured. Exiting..."
            raise Exception

        os.system("cp " + APLUS_HOME + "aplus.db_copy" + " " + APLUS_HOME + "aplus.db")

    def getLocalConfigHomePath(self):
        try:
            config = ConfigParser.RawConfigParser()
            config.read('local_test.cfg')
            return config.get('Selenium Local Environment', 'APLUS_HOME')
        except ConfigParser.NoSectionError:
            print 'local_test.cfg not found.'
