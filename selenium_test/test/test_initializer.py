import os
import enum
from selenium.webdriver import Chrome, Firefox, ChromeOptions, FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

TEST_PATH = os.path.dirname(os.path.dirname(__file__))
TEST_DB = os.path.join(TEST_PATH, 'aplus.db')
TEST_COPY = os.path.join(TEST_PATH, 'aplus.db_copy')

class Browser(enum.Enum):
    firefox = "Firefox"
    chrome = "Chrome"

class TestInitializer:

    def getDefaultDriver(self, headless: bool = False, browser: str = "Firefox") -> WebDriver:
        driver = self.getDriver(headless, browser)
        driver.set_window_size(1024,768)
        return driver

    def setupDisplay(self):
        # Headless with xvfb. Alternatively may just xvfb-run python.
        from pyvirtualdisplay import Display # pylint: disable=import-outside-toplevel
        display = Display(visible = False, size = (1024,768))
        display.start()

    def getDriver(self, headless: bool = False, browser: str = "Firefox") -> WebDriver:
        print('Browser: ' + browser)

        if Browser.firefox.value == browser:
            options = FirefoxOptions()
            if headless:
                options.add_argument('-headless')
            driver = Firefox(options=options)
        elif Browser.chrome.value == browser:
            options = ChromeOptions()
            if headless:
                options.add_argument('-headless')
            driver = Chrome(chrome_options=options)
        else:
            raise ValueError(f"Browser value {browser} unknown")

        return driver

    # This just replaces the current database with a copy.
    # TODO Should use Django unit tests that run selenium.
    def recreateDatabase(self) -> None:
        if not os.path.exists(TEST_DB):
            raise Exception( # pylint: disable=broad-exception-raised
                'The A+ Django needs to be run with environment variable APLUS_DB_FILE=selenium_test/aplus.db'
            )
        if not os.path.exists(TEST_COPY):
            os.system("cp " + TEST_DB + " " + TEST_COPY)
        os.system("cp " + TEST_COPY + " " + TEST_DB)
