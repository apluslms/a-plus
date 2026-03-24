import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_should_not_count_empty_submit(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Course materials").click()
    first_link = page.get_by_role("link", name="AJAX exercises: grading in browser JavaScript").first
    first_link.click()

    page.get_by_role("button", name="Submit").click()

    submissions = page.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("0 / 20")
    #empty submit should not count as submission

    points = page.locator('#chapter-exercise-1').get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("0 / 10")


def test_should_give_full_points_on_correct_answer(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    # page.goto("http://localhost:8000/def/current/programming_exercises/ajax_exercise/")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Course materials").click()
    first_link = page.get_by_role("link", name="AJAX exercises: grading in browser JavaScript").first
    first_link.click()

    page.get_by_role("textbox").fill("abc")
    page.get_by_role("button", name="Submit").click()

    submissions = page.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("1 / 20")

    points = page.locator('#chapter-exercise-1').get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("10 / 10")
