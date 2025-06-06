from playwright.sync_api import Page, expect
from e2e_tests.helpers import login, navigate_to_default_course


def test_edit_module_page(page: Page) -> None:
    page.goto("http://localhost:8000/?hl=en")
    login(page, "teacher", "teacher")

    navigate_to_default_course(page)
    page.get_by_role("link", name="Edit course").click()

    # Click the first assignment edit button as we don't know which ids are
    # exercises (not chapters) at this point
    page.get_by_role("button").filter(has_text="Edit module").first.click()

    exerciseName = "Testimoduuli"
    introduction = "Tämä on testimoduuli."
    pointsToPass = "94"

    # Fill in new exercise details
    page.get_by_placeholder("Name").fill(exerciseName)
    page.get_by_placeholder("Introduction").fill(introduction)
    page.get_by_placeholder("Points to pass").fill(pointsToPass)
    page.get_by_placeholder("Late submission penalty").fill('0.33')
    page.locator('id=id_model_solution-currently_revealed').check()
    page.locator('id=id_model_solution-show_zero_points_immediately').check()

    page.get_by_role("button", name="Save").click()

    # Check for a successful save message
    expect(page.locator(".site-message")).to_contain_text("The module was saved successfully.")

    # Check that the exercise details were saved correctly
    page.get_by_role("button").filter(has_text="Edit module").first.click()

    expect(page.get_by_placeholder("Name")).to_have_value(exerciseName)
    expect(page.get_by_placeholder("Introduction")).to_have_value(introduction)
    expect(page.get_by_placeholder("Points to pass")).to_have_value(pointsToPass)
    expect(page.get_by_placeholder("Late submission penalty")).to_have_value('0.33')
    expect(page.locator('id=id_model_solution-currently_revealed')).to_be_checked()
    expect(page.locator('id=id_model_solution-show_zero_points_immediately')).to_be_checked()