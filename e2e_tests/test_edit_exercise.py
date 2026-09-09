import re

from playwright.sync_api import Page, expect
from e2e_tests.helpers import login, navigate_to_default_course, logout


def test_edit_exercise(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")
    login(page, "student", "student")

    navigate_to_default_course(page)
    page.get_by_role("link", name="5.2 Question groups").first.click()

    # Target exercise 5.2.2 from the chapter exercise list.
    exercise = page.locator("#chapter-exercise-2")
    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    points = exercise.get_by_role("button", name=re.compile("Points"))

    # Verify current values before editing.
    expect(submissions).to_contain_text("0 / 10")
    expect(points).to_contain_text("0 / 30")


    #edit values as teacher
    logout(page)
    login(page, "teacher", "teacher")
    navigate_to_default_course(page)
    page.locator("#main-course-menu").get_by_role("link", name="Edit course").click()
    page.locator("tr").filter(
        has_text="5.2.2 Question groups"
    ).get_by_role("button", name="Edit assignment").click()

    page.locator("#id_max_points").fill("50")
    page.locator("#id_max_submissions").fill("5")

    page.get_by_role("button", name="Save").click()

    #check edited values as student
    logout(page)
    login(page, "student", "student")

    navigate_to_default_course(page)
    page.get_by_role("link", name="5.2 Question groups").first.click()

    # Target exercise 5.2.2 from the chapter exercise list.
    exercise = page.locator("#chapter-exercise-2")
    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    points = exercise.get_by_role("button", name=re.compile("Points"))

    # Verify new values after editing.
    expect(submissions).to_contain_text("0 / 5")
    expect(points).to_contain_text("0 / 50")
