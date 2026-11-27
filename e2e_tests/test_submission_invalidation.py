import re

from playwright.sync_api import Page, expect
from e2e_tests.helpers import login, logout, navigate_to_default_course

def test_submission_invalidation(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")

    #first log in as assistant and submit an exercise
    #(don't use student login as all questionaires are filled as student in other tests)


    #TODO
    login(page, "assistant", "assistant")
    navigate_to_default_course(page)
    page.get_by_role("link", name="6.9 AJAX exercises: grading in browser JavaScript").first.click()

    page.get_by_role("textbox").fill("abc")
    page.get_by_role("button", name="Submit").click()

    #check point totals
    submissions = page.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("1 / 20")

    points = page.locator('#chapter-exercise-1').get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("10 / 10")

    #then log in as teacher and invalidate the submission
    logout(page)
    login(page, "teacher", "teacher")
    navigate_to_default_course(page)

    page.get_by_role("link", name="All submissions").click()

    submission_table = page.locator("#submissions_table")

    top_row = submission_table.locator("tbody > tr").first
    expect(top_row).to_contain_text("Andy Assistant")
    expect(top_row).to_contain_text("6.9.1 Example AJAX exercise")

    top_row.get_by_role("link", name="Inspect").click()
    page.get_by_role("button", name="Invalidate submission").click()
    page.get_by_role("button", name="Yes").click()

    #then recheck point totals as assistant (expected 0 points)
    logout(page)
    login(page, "assistant", "assistant")
    navigate_to_default_course(page)

    page.get_by_role("link", name="6.9 AJAX exercises: grading in browser JavaScript").first.click()

    submissions = page.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("1 / 20")

    points = page.locator('#chapter-exercise-1').get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("0 / 10")