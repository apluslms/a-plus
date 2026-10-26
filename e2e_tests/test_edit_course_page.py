from playwright.sync_api import Page, expect
from e2e_tests.helpers import login, navigate_to_default_course


def test_edit_course_invalid_start_date(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")
    login(page, "teacher", "teacher")

    navigate_to_default_course(page)
    page.get_by_role("link", name="Edit course").click()

    page.locator(".menu-course-details.nav-item").filter(has_text="Course").first.click()

    # Course starting time
    START_DATE = "3000-01-01T12:00"

    page.locator("id=id_starting_time").fill(START_DATE)

    page.get_by_role("button", name="Save").click()

    # Check that the page displays an error
    expect(page.locator(".site-message")).to_contain_text("Failed to save changes.")
    expect(page.locator(".invalid-feedback").first).to_contain_text("The course ending\
    time must be later than the course starting time.")

    # Check that the course teachers and assistants are still selected
    expect(page.locator("id=id_teachers_badges")).to_have_count(1)
    expect(page.locator("id=id_assistants_badges")).to_have_count(1)


def test_save_course_details(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")
    login(page, "teacher", "teacher")

    navigate_to_default_course(page)
    page.get_by_role("link", name="Edit course").click()

    page.locator(".menu-course-details.nav-item").filter(has_text="Course").first.click()

    page.get_by_role("button", name="Save").click()

    # Check that the page displays the correct message
    expect(page.locator(".site-message")).to_contain_text("Changes were saved successfully.")
