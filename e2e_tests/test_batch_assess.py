from playwright.sync_api import Page, expect
from e2e_tests.helpers import login, navigate_to_default_course, logout
import re

def test_batch_assess(page: Page) -> None: # pylint: disable=too-many-statements
    page.goto("http://localhost:8010/?hl=en")
    login(page, "teacher", "teacher")

    navigate_to_default_course(page)
    page.get_by_role("link", name="Participants").click()

    #select 3 students (one of them Stacy Student) and first check that
    #2 have no points and that all have no submissions on exercise 6.10.1

    page.get_by_role("link", name="11110001").click()

    expect(page.get_by_role("navigation", name="Breadcrumb")).to_contain_text("Zac Singh")

    cards = page.locator("div.card")
    expect(cards.filter(has_text="jututfeedback")).to_contain_text("0 / 4")
    expect(cards.filter(has_text="questionnaire")).to_contain_text("0 / 97")
    expect(cards.filter(has_text="submit")).to_contain_text("0 / 750")

    exercise_row = (page.get_by_role("link", name="6.10.1 (Git) Hello Python!").locator("xpath=ancestor::tr"))
    expect(exercise_row).to_contain_text("submit 0 / 10 No submissions yet 0 / 10")

    page.get_by_role("link", name="Participants").first.click()
    page.get_by_role("link", name="11110002").click()

    expect(page.get_by_role("navigation", name="Breadcrumb")).to_contain_text("Felicity Moran")

    cards = page.locator("div.card")
    expect(cards.filter(has_text="jututfeedback")).to_contain_text("0 / 4")
    expect(cards.filter(has_text="questionnaire")).to_contain_text("0 / 97")
    expect(cards.filter(has_text="submit")).to_contain_text("0 / 750")

    exercise_row = (page.get_by_role("link", name="6.10.1 (Git) Hello Python!").locator("xpath=ancestor::tr"))
    expect(exercise_row).to_contain_text("submit 0 / 10 No submissions yet 0 / 10")

    page.get_by_role("link", name="Participants").first.click()
    page.locator('input[data-column="1"]').fill("123456")
    page.get_by_role("link", name="123456").click()

    expect(page.get_by_role("navigation", name="Breadcrumb")).to_contain_text("Stacy Student")

    #don't verify Stacy Student's point totals since other tests affect them

    exercise_row = (page.get_by_role("link", name="6.10.1 (Git) Hello Python!").locator("xpath=ancestor::tr"))
    expect(exercise_row).to_contain_text("submit 0 / 10 No submissions yet 0 / 10")

    page.get_by_role("link", name="Participants").first.click()
    #first select all 3 students
    page.locator("select.form-select.form-select-sm").select_option("-1")

    row1 = page.locator("tr").filter(has_text="11110001")
    row1.get_by_role("checkbox").check()

    row2 = page.locator("tr").filter(has_text="11110002")
    row2.get_by_role("checkbox").check()

    row3 = page.locator("tr").filter(has_text="123456")
    row3.get_by_role("checkbox").check()

    #then do the batch assessment (exercise 6.10.1, with message)

    page.get_by_role("button", name="Batch assess").click()
    page.locator("#batch-assess-category").select_option(
        label="6.10.1 (Git) Hello Python!"
    )
    page.locator("#batch-assess-value-display").fill("7")
    page.locator("#batch-assess-feedback").fill("good job")
    page.get_by_role("button", name="Submit").click()

    expect(page.get_by_role("heading", name="Batch assessment successful")).to_be_visible()

    expect(page.locator("#batch-assess-success-count")).to_have_text("3")
    expect(page.locator("#batch-assess-success-exercise")).to_have_text(
        "6.10.1 (Git) Hello Python!"
    )
    expect(page.locator("#batch-assess-success-students")).to_contain_text(
        "Zac Singh (ID: 7)"
    )
    expect(page.locator("#batch-assess-success-students")).to_contain_text(
        "Felicity Moran (ID: 8)"
    )
    expect(page.locator("#batch-assess-success-students")).to_contain_text(
        "Stacy Student (ID: 5)"
    )
    expect(page.locator("#batch-assess-success-points")).to_have_text("7")
    expect(page.locator("#batch-assess-success-feedback")).to_have_text("good job")

    page.get_by_role("button", name="Close").first.click()

    #then check as teacher that the points and submissions are correct

    page.get_by_role("link", name="11110001").click()

    expect(page.get_by_role("navigation", name="Breadcrumb")).to_contain_text("Zac Singh")

    cards = page.locator("div.card")
    expect(cards.filter(has_text="jututfeedback")).to_contain_text("0 / 4")
    expect(cards.filter(has_text="questionnaire")).to_contain_text("0 / 97")
    expect(cards.filter(has_text="submit")).to_contain_text("7 / 750")

    exercise_row = (page.get_by_role("link", name="6.10.1 (Git) Hello Python!").locator("xpath=ancestor::tr"))
    expect(exercise_row).to_contain_text("1 / 10")
    expect(exercise_row).to_contain_text("7 / 10")

    page.get_by_role("link", name="Participants").first.click()
    page.get_by_role("link", name="11110002").click()

    expect(page.get_by_role("navigation", name="Breadcrumb")).to_contain_text("Felicity Moran")

    cards = page.locator("div.card")
    expect(cards.filter(has_text="jututfeedback")).to_contain_text("0 / 4")
    expect(cards.filter(has_text="questionnaire")).to_contain_text("0 / 97")
    expect(cards.filter(has_text="submit")).to_contain_text("7 / 750")

    exercise_row = (page.get_by_role("link", name="6.10.1 (Git) Hello Python!").locator("xpath=ancestor::tr"))
    expect(exercise_row).to_contain_text("1 / 10")
    expect(exercise_row).to_contain_text("7 / 10")

    #don't check Stacy Student's points since other tests affect them
    #then logout and check as student that the points, message and submissions are correct

    logout(page)
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="6.10 Submit from Git").click()

    exercise = page.locator('#chapter-exercise-1')
    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    points = exercise.get_by_role("button", name=re.compile("Points"))

    expect(submissions).to_contain_text("1 / 10")
    expect(points).to_contain_text("7 / 10")

    submissions.click()
    exercise.locator(".dropdown-menu li a.page-modal").click()

    points_dialog = page.get_by_role("dialog").filter(has_text="6.10.1")
    expect(points_dialog).to_contain_text("good job")
    