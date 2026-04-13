import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login
#this is a test done to represent the 'my-first-exercise-test.py' in the old Selenium tests



def test_should_not_accept_empty_submission(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="5.1 Creating questionnaire exercises").first.click()

    #fill in an empty answer for exercise 5.1.2
    exercise = page.locator("#chapter-exercise-2")
    exercise.get_by_role("textbox", name="Question 1").fill("")
    exercise.get_by_role("textbox", name="Question 2").fill("")
    exercise.get_by_role("textbox", name="Question 3").fill("")
    exercise.get_by_role("textbox", name="Question 4").fill("")
    exercise.get_by_role("textbox", name="Question 5").fill("")
    exercise.get_by_role("textbox", name="Question 6").fill("")
    exercise.get_by_role("button", name="Submit").click()

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("0 / 3") #empty submission doesn't count
    #NOTE: this could fail if the test is run after the 'test_should_give_zero_points_on_false_submission' test
    #This is a problem with the tests not being independent of each other

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("0 / 25")


def test_should_give_zero_points_on_false_submission(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="5.1 Creating questionnaire exercises").first.click()

    #fill in an false answer for exercise 5.1.2
    exercise = page.locator("#chapter-exercise-2")
    exercise.get_by_role("textbox", name="Question 1").fill("z")
    exercise.get_by_role("textbox", name="Question 2").fill("z")
    exercise.get_by_role("textbox", name="Question 3").fill("z")
    exercise.get_by_role("textbox", name="Question 4").fill("1")
    exercise.get_by_role("textbox", name="Question 5").fill("1")
    exercise.get_by_role("textbox", name="Question 6").fill("1")
    exercise.get_by_role("button", name="Submit").click()

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("1 / 3") #false submission counts

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("0 / 25")


def test_should_give_partial_points_on_partially_correct_submission(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="5.1 Creating questionnaire exercises").first.click()

    #fill in an partially correct answer for exercise 5.1.3
    #fill in different exercise to make the test work independently of the previous test
    # TODO: figure out a way to make the tests independent?
    exercise = page.locator("#chapter-exercise-3")
    exercise.get_by_role("textbox", name="Question 1").fill("anothertest")
    exercise.get_by_role("textbox", name="Question 2").fill("a")
    exercise.get_by_role("button", name="Submit").click()

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("1 / 5") #partially correct submission counts

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("5 / 10")


def test_should_give_full_points_on_correct_submission(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="5.1 Creating questionnaire exercises").first.click()

    #fill in an correct answer for exercise 5.1.4
    #fill in different exercise to make the test work independently of the previous test
    # TODO: figure out a way to make the tests independent?
    exercise = page.locator("#chapter-exercise-4")
    exercise.get_by_role("textbox", name="Question 1").fill("cat")
    exercise.get_by_role("textbox", name="Question 2").fill("3.141")
    exercise.get_by_role("button", name="Submit").click()

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("1 / 5") #correct submission counts

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("20 / 20")


def test_should_not_accept_submission_after_max_submissions_reached(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="5.1 Creating questionnaire exercises").first.click()

    #fill in an false answer for exercise 5.1.2 until max submissions reached
    exercise = page.locator("#chapter-exercise-2")

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))

    if "0" in submissions.inner_text():
        sub_count = 0
    elif "1" in submissions.inner_text():
        sub_count = 1
    elif "2" in submissions.inner_text():
        sub_count = 2
    else:
        sub_count = 3
    #max submissions already reached, this can happen if the test is run after other tests

    while (sub_count < 3):
        exercise.get_by_role("textbox", name="Question 1").fill("z")
        exercise.get_by_role("textbox", name="Question 2").fill("z")
        exercise.get_by_role("textbox", name="Question 3").fill("z")
        exercise.get_by_role("textbox", name="Question 4").fill("1")
        exercise.get_by_role("textbox", name="Question 5").fill("1")
        exercise.get_by_role("textbox", name="Question 6").fill("1")
        exercise.get_by_role("button", name="Submit").click()

        identical_submission_warning = page.get_by_role("dialog", name = "Identical submission")
        if identical_submission_warning.is_visible():
            identical_submission_warning.get_by_role("button", name="Submit").click()
        sub_count += 1

    expect(submissions).to_contain_text("3 / 3") #max submissions reached

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("0 / 25")

    #try to submit correct answer after max submissions reached
    exercise.get_by_role("textbox", name="Question 1").fill("test")
    exercise.get_by_role("textbox", name="Question 2").fill("textbox")
    exercise.get_by_role("textbox", name="Question 3").fill("required")
    exercise.get_by_role("textbox", name="Question 4").fill("11")
    exercise.get_by_role("textbox", name="Question 5").fill("0.375")
    exercise.get_by_role("textbox", name="Question 6").fill("0.375")
    exercise.get_by_role("button", name="Submit").click()

    expect(submissions).to_contain_text("3 / 3")
    expect(points).to_contain_text("0 / 25")

    #test that 3 submissions are also shown in the 'My Submissions' dropdown
    submissions.click()
    dropdown_menu = exercise.locator(".dropdown-menu")
    submission_list = dropdown_menu.get_by_role("listitem")
    expect(submission_list).to_have_count(3)