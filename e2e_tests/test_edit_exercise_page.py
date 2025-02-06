from playwright.sync_api import Page, expect
from e2e_tests.helpers import login, navigate_to_default_course


def test_edit_exercise_page(page: Page) -> None:
    page.goto("http://localhost:8000/?hl=en")
    login(page, "teacher", "teacher")

    navigate_to_default_course(page)
    page.get_by_role("link", name="Edit course").click()

    # Click the first assignment edit button as we don't know which ids are
    # exercises (not chapters) at this point
    page.get_by_role("button").filter(has_text="Edit assignment").first.click()

    # Get the exercise number from the URL we navigated to via previous button click
    exerciseNumber = page.url.split("/")[-2]

    exerciseName = "Testiharjoitus"
    maxSubmissions = "5"
    maxPoints = "99"
    pointsToPass = "50"

    # Fill in new exercise details
    page.get_by_placeholder("Name").fill(exerciseName)
    page.get_by_placeholder("Max submissions").fill(maxSubmissions)
    page.get_by_placeholder("Max points").fill(maxPoints)
    page.get_by_placeholder("Points to pass").fill(pointsToPass)
    page.get_by_role("button", name="Save").click()

    page.goto(
        "http://localhost:8000/def/current/teachers/exercise/" 
        + str(exerciseNumber)
        + "/"
    )

    # Check that the exercise details were saved correctly
    expect(page.get_by_placeholder("Name")).to_have_value(exerciseName)
    expect(page.get_by_placeholder("Max submissions")).to_have_value(maxSubmissions)
    expect(page.get_by_placeholder("Max points")).to_have_value(maxPoints)
    expect(page.get_by_placeholder("Points to pass")).to_have_value(pointsToPass)
