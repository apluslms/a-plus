import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_should_not_submit_without_files(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Course materials").click()
    first_link = page.get_by_role("link", name="Exercises with Python grader utils").first
    first_link.click()

    page.locator('#chapter-exercise-1').get_by_role("button", name="Submit").click()

    submissions = page.locator('#chapter-exercise-1').get_by_role("button", name=re.compile("My submissions"))
    points = page.locator('#chapter-exercise-1').get_by_role("button", name=re.compile("Points"))

    expect(submissions).to_contain_text("0 / 10")
    #clicking submit without files will not result in a submission
    expect(points).to_contain_text("0 / 10")

#TODO more tests ?
    
    


    



