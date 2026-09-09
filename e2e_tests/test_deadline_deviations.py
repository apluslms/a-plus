from playwright.sync_api import Page, expect
from e2e_tests.helpers import login, logout, navigate_to_default_course
from datetime import datetime

def test_deadline_deviations(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")

    #first check as student that there is no deadline deviation
    login(page, "student", "student")
    navigate_to_default_course(page)
    expect(page.locator("#course-content")).not_to_contain_text("Assignments with personal deadline extensions")
    page.get_by_role("link", name="6.2 Hello Worlds").first.click()

    exercise = page.locator("#chapter-exercise-1")
    info = exercise.locator("div.container-fluid.bg-info-subtle.text-info-emphasis")
    expect(info).not_to_contain_text("Personal extended")
    expect(info).to_contain_text("Deadline Tuesday, 31 December 2030, 12:00")

    #create deadline deviation as teacher
    logout(page)
    login(page, "teacher", "teacher")

    navigate_to_default_course(page)
    page.get_by_role("link", name="Deadline deviations").click()
    page.get_by_role("button", name="Add new deadline deviations").click()

    #create the deviation
    exercise_input = page.locator("#id_exercise_wrapper")
    exercise_input.get_by_role("textbox").fill("6.2.1 Hello Python!")
    exercise_input.get_by_role("button", name="Search").click()
    exercise_input.get_by_role("link", name="6.2.1 Hello Python!").click()

    submitter_input = page.locator("#id_submitter_wrapper")
    submitter_input.get_by_role("textbox").fill("Stacy Student, 123456, student@localhost.invalid")
    submitter_input.get_by_role("button", name="Search").click()
    submitter_input.get_by_role("link", name="Stacy Student, 123456, student@localhost.invalid").click()

    current_year = datetime.now().year
    page.locator("#id_new_date").fill(f"{current_year}-12-31T12:00")

    page.get_by_role("button", name="Save").click()

    #lastly check as student that the deadline deviation is visible
    logout(page)
    login(page, "student", "student")
    navigate_to_default_course(page)

    expect(page.locator("#course-content")).to_contain_text("Assignments with personal deadline extensions")

    page.get_by_role("link", name="6.2 Hello Worlds").first.click()

    exercise = page.locator("#chapter-exercise-1")
    info = exercise.locator("div.container-fluid.bg-info-subtle.text-info-emphasis")
    expect(info).to_contain_text("Personal extended deadline")
    expect(info).to_contain_text(f"31 December {current_year}, 12:00")