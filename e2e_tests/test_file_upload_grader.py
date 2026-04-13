import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import File, navigate_to_default_course, login, upload_submission


def test_should_not_submit_without_files(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Course materials").click()
    first_link = page.get_by_role("link", name="Exercises with Python grader utils").first
    first_link.click()

    exercise = page.locator('#chapter-exercise-1')

    exercise.get_by_role("button", name="Submit").click()

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    points = exercise.get_by_role("button", name=re.compile("Points"))

    expect(submissions).to_contain_text("0 / 10")
    #clicking submit without files will not result in a submission
    expect(points).to_contain_text("0 / 10")

def test_should_give_zero_points_on_incorrect_answer(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)

    upload_submission(
        page,
        chapter_name="6.3 Exercises with Python",
        exercise_name="#chapter-exercise-1",
        files=[File("functions2.py", "functions.py")]
    )

    exercise = page.locator('#chapter-exercise-1')
    points = exercise.get_by_role("button", name=re.compile("Points"))

    #the submission should be incorrect and give zero points
    expect(points).to_contain_text("0 / 10")


def test_should_give_full_points_on_correct_answer(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)

    upload_submission(
        page,
        chapter_name="6.3 Exercises with Python",
        exercise_name="#chapter-exercise-1",
        files=[File("functions.py")]
    )

    exercise = page.locator('#chapter-exercise-1')
    points = exercise.get_by_role("button", name=re.compile("Points"))

    #the submission should be correct and give full points
    expect(points).to_contain_text("10 / 10")