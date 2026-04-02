import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_homepage(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    expect(page).to_have_title(re.compile("A+"))

    login(page, "student", "student")
    navigate_to_default_course(page)
    expect(page.get_by_role("heading", name="A+ Manual")).to_be_visible()
    #TODO figure out more testing for the homepage