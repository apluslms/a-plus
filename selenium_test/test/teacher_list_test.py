from datetime import date, timedelta
from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
import unittest

from locators import CommonLocators
from page_objects import LoginPage, BasePage
from test_initializer import TestInitializer


class TeacherListPage(BasePage):
    def __init__(
            self,
            driver: WebDriver,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            with_assistants: bool = False
            ) -> None:
        BasePage.__init__(self, driver)

        query: List[str] = []
        if start_date:
            query.append("start_date=" + start_date.isoformat())
        if end_date:
            query.append("end_date=" + end_date.isoformat())
        query.append("with_assistants=" + ("true" if with_assistants else "false"))

        self.load("/accounts/teachers/?" + "&".join(query), (By.CSS_SELECTOR, '.page-header'))

    def get_table_data(self) -> List[List[str]]:
        rows = self.getElements((By.CSS_SELECTOR, "table tbody tr"))
        data: List[List[str]] = []
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            data.append([c.text for c in cells])
        return data


class TeacherListTest(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = TestInitializer().getDefaultDriver(headless=True)
        TestInitializer().recreateDatabase()

    def testAnonymousCantAccess(self) -> None:
        self.assertTrue(TeacherListPage(self.driver).isElementPresent(CommonLocators.PERMISSION_DENIED_ACCESS_MODE))

    def testStudentsCantAccess(self) -> None:
        LoginPage(self.driver).loginAsStudent()
        self.assertTrue(TeacherListPage(self.driver).isElementPresent(CommonLocators.FORBIDDEN_PAGE))

    def testTeachersCantAccess(self) -> None:
        LoginPage(self.driver).loginAsTeacher()
        self.assertTrue(TeacherListPage(self.driver).isElementPresent(CommonLocators.FORBIDDEN_PAGE))

    def testSuperusersCanAccess(self) -> None:
        LoginPage(self.driver).loginAsSuperuser()
        self.assertFalse(TeacherListPage(self.driver).isElementPresent(CommonLocators.FORBIDDEN_PAGE))

    def testTableHasCorrectData(self) -> None:
        LoginPage(self.driver).loginAsSuperuser()

        list_data = [
            [
                'Teacher User',
                '',
                'aplus-001 My test course: A+ Test Course Instance',
                '2020-09-27 09:00:00+00:00',
                '2023-09-27 09:00:00+00:00'
            ],
            [
                'Teacher User',
                '',
                'aplus-001 My test course: Hook Example',
                '2020-09-27 09:00:00+00:00',
                '2023-09-27 09:00:00+00:00'
            ],
        ]
        list_data_with_assistants = [
            [
                'Teacher User',
                '',
                'aplus-001 My test course: A+ Test Course Instance',
                '2020-09-27 09:00:00+00:00',
                '2023-09-27 09:00:00+00:00'
            ],
            [
                'Assistant User',
                '',
                'aplus-001 My test course: A+ Test Course Instance',
                '2020-09-27 09:00:00+00:00',
                '2023-09-27 09:00:00+00:00'
            ],
            [
                'Teacher User',
                '',
                'aplus-001 My test course: Hook Example',
                '2020-09-27 09:00:00+00:00',
                '2023-09-27 09:00:00+00:00'
            ],
        ]

        ending_time = date.fromisoformat("2023-09-27")
        starting_time = date.fromisoformat("2020-09-27")

        early = starting_time - timedelta(days=1)
        middle_early = starting_time + timedelta(days=1)
        middle_late = ending_time - timedelta(days=1)
        late = ending_time + timedelta(days=1)

        data = TeacherListPage(self.driver, starting_time, starting_time).get_table_data()
        self.assertEqual(data, list_data)

        data = TeacherListPage(self.driver, ending_time, ending_time).get_table_data()
        self.assertEqual(data, list_data)

        data = TeacherListPage(self.driver, early, early).get_table_data()
        self.assertEqual(data, [])

        data = TeacherListPage(self.driver, late, late).get_table_data()
        self.assertEqual(data, [])

        data = TeacherListPage(self.driver, middle_late, late).get_table_data()
        self.assertEqual(data, list_data)

        data = TeacherListPage(self.driver, early, middle_early).get_table_data()
        self.assertEqual(data, list_data)

        data = TeacherListPage(self.driver, early, middle_early, True).get_table_data()
        self.assertEqual(data, list_data_with_assistants)

    def tearDown(self) -> None:
        self.driver.quit()


if __name__ == '__main__':
    unittest.main(verbosity=2)
