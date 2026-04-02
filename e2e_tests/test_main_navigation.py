import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_main_navigation(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "teacher", "teacher")
    navigate_to_default_course(page)

    page.get_by_role("link", name="Your points").click()
    expect(page).to_have_url(re.compile("/user/results/"))
    navigate_to_default_course(page)

    page.get_by_role("link", name="All results").click()
    expect(page).to_have_url(re.compile("/teachers/results/"))

    #TODO test rest of links? Also student view?
    