import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login
#this is a test done to represent the 'my-first-exercise-test.py' in the old Selenium tests



def test_submission_count(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="5.2 Question groups").click()
    
    #fill in an answer 11 times for exercise 5.2.1
    exercise = page.locator("#chapter-exercise-1")

    sub_count = 0

    while (sub_count <= 10):

        submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
        expect(submissions).to_contain_text(f"{sub_count} / 10")

        points = exercise.get_by_role("button", name=re.compile("Points"))

        if (sub_count == 0):
            expect(points).to_contain_text("0 / 15")
        else:
            expect(points).to_contain_text("10 / 15")

        exercise.get_by_role("radio", name="2").check() #question 1

        q2 = exercise.get_by_label(re.compile(r"2.*7.*?"))
        q2.select_option("14")

        q3 = exercise.locator(".question-area", has_text=re.compile(r"2.*x.*y"))
        q3.locator("input[type='checkbox'][value='option_0']").check()
        q3.locator("input[type='checkbox'][value='option_2']").check()

        exercise.get_by_role("textbox").fill("15") #question 4

        exercise.get_by_role("radio", name="8").check() #question 5

        q5 = exercise.get_by_label(re.compile(r"4.*8.*?"))
        q5.select_option("28")

        exercise.get_by_role("button", name="Submit").click()

        identical_warning = page.get_by_role("dialog", name = "Identical submission")
        if identical_warning.is_visible():
            identical_warning.get_by_role("button", name="Submit").click()

        sub_count += 1

    #the 11th time should result in a failure

    submissions = exercise.get_by_role("button", name=re.compile("My submissions"))
    expect(submissions).to_contain_text("10 / 10")

    points = exercise.get_by_role("button", name=re.compile("Points"))
    expect(points).to_contain_text("10 / 15")
        

        