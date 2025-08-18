import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course


def test_frontpage_has_title(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    expect(page).to_have_title(re.compile("A+"))


def test_course_has_heading(page: Page) -> None:
    page.goto("http://localhost:8000/?hl=en")
    navigate_to_default_course(page)
    expect(page.get_by_role("heading", name="A+ Manual")).to_be_visible()
