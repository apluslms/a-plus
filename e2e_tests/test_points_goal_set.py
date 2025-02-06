from playwright.sync_api import Page, expect

from e2e_tests.helpers import login, navigate_to_default_course


def test_points_goal_set(page: Page) -> None:
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")

    navigate_to_default_course(page)
    page.get_by_role("link", name="Your points").click()
    page.locator("#progress-questionnaires").get_by_role("button", name="Points goal").click()
    page.get_by_label("Input personalized goal as").fill("50")
    page.get_by_label("Input personalized goal as").press("Tab")
    page.get_by_role("button", name="Save").click()
    expect(page.locator("#success-alert")).to_contain_text("Succesfully set personalized points goal")
    page.get_by_role("button", name="Close", exact=True).click()
    expect(page.get_by_text("Points goal: 50"))
    expect(page.locator("#goal-points"))


def test_points_goal_reached(page: Page) -> None:
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Creating questionnaire exercises").click()
    page.locator("label").filter(has_text="2").first.click()
    page.locator("label").filter(has_text="an integer").first.click()
    page.locator("div:nth-child(4) > div:nth-child(6) > label").click()
    page.locator("label").filter(has_text="-").nth(1).click()
    page.locator("label").filter(has_text="an integer").nth(1).click()
    page.locator("div:nth-child(5) > div:nth-child(6) > label").click()
    page.locator("label").filter(has_text="-").nth(3).click()
    page.locator("#chapter-exercise-1").get_by_role("button", name="Submit").click()
    expect(page.get_by_label("5.1.1 Single-choice and")).to_contain_text("30 / 40")
    page.get_by_role("link", name="Your points").click()
    page.locator("#progress-questionnaires").get_by_role("button", name="Points goal").click()
    page.get_by_label("Input personalized goal as").fill("30")
    page.get_by_role("button", name="Save").click()
    expect(page.locator("#success-alert")).to_contain_text("Succesfully set personalized points goal")
    page.get_by_role("button", name="Close", exact=True).click()
    progress_bar_locator = page.locator("#progress-questionnaires > .progress > .aplus-progress-bar")
    expect(progress_bar_locator).\
        to_have_class("aplus-progress-bar aplus-progress-bar-striped aplus-progress-bar-primary")
