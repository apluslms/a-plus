import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_homepage(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    expect(page).to_have_title(re.compile("A+"))

    login(page, "student", "student")
    navigate_to_default_course(page)
    expect(page.get_by_role("heading", name="A+ Manual")).to_be_visible()

   # point_values = page.locator("div.col-xl-3") these don't work reliably in the suite
   # expect(point_values).to_contain_text("jututfeedback 0 / 4")
   # expect(point_values).to_contain_text("questionnaire 0 / 97")
   # expect(point_values).to_contain_text("submit 0 / 700")

   #TODO figure out more testing for the homepage