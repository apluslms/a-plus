import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login, logout


def test_grading_modes(page: Page):
    page.goto("http://localhost:8010/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="5.1 Creating questionnaire exercises").first.click()

    #login as student and make two submissions to exercise 5.1.4
    #first with max points and second with partial points

    exercise = page.locator("#chapter-exercise-4")

    exercise.get_by_role("textbox", name="Question 1").fill("dog")
    exercise.get_by_role("textbox", name="Question 2").fill("3.141")

    exercise.get_by_role("button", name="Submit").click()

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("1 / 5")

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("20 / 20")

    exercise.get_by_role("textbox", name="Question 1").fill("dog")
    exercise.get_by_role("textbox", name="Question 2").fill("3.142")

    exercise.get_by_role("button", name="Submit").click()

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("2 / 5")

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("20 / 20")

    #then login as teacher and change the grading mode to latest submission

    logout(page)
    login(page, "teacher", "teacher")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Edit course").click()

    page.locator("tr").filter(
        has_text="Questionnaire using regular expressions"
    ).get_by_role("button", name="Edit assignment").click()
    page.locator("#id_grading_mode").select_option("2")
    page.get_by_role("button", name="Save").click()


    #login as student and re-check exercise, should have partial points
    logout(page)
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="5.1 Creating questionnaire exercises").first.click()

    exercise = page.locator("#chapter-exercise-4")

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("2 / 5")

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("10 / 20")