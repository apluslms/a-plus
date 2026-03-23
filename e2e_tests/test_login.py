import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_login(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    expect(page).to_have_title(re.compile("A+"))
    expect(page.get_by_label("Main")).to_contain_text("Stacy Student")

def test_false_login(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "fake", "fake")
    expect(page).to_have_title(re.compile("Log in to A+ | A+"))
    expect(page.locator("div.alert.alert-danger.alert-dismissible")).to_contain_text("Please enter a correct username and password. Note that both fields may be case-sensitive.")
