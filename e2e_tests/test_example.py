import re
from playwright.sync_api import Page, expect


def test_frontpage_has_title(page: Page):
    page.goto("http://localhost:8000/")
    expect(page).to_have_title(re.compile("A+"))


def test_course_has_heading(page: Page) -> None:
    page.goto("http://localhost:8000/")
    page.get_by_role("link", name="Def. Course Current DEF000 1.").click()
    expect(page.get_by_role("heading", name="A+ Manual")).to_be_visible()
