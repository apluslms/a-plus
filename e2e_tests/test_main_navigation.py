import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_main_navigation(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "teacher", "teacher")
    navigate_to_default_course(page)
    sidebar = page.locator("#main-course-menu")

    sidebar.get_by_role("link", name="Course materials").click()
    expect(page).to_have_url(re.compile("/toc/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="Your points").click()
    expect(page).to_have_url(re.compile("/user/results/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="Participants").click()
    expect(page).to_have_url(re.compile("/teachers/participants/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="Groups").click()
    expect(page).to_have_url(re.compile("/teachers/groups/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="All results").click()
    expect(page).to_have_url(re.compile("/teachers/results/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="Visualizations").click()
    expect(page).to_have_url(re.compile("/teachers/analytics/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="Edit news").click()
    expect(page).to_have_url(re.compile("/teachers/news/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="Edit course").click()
    expect(page).to_have_url(re.compile("/teachers/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="Deadline deviations").click()
    expect(page).to_have_url(re.compile("/teachers/deadline-deviations/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="Submission deviations").click()
    expect(page).to_have_url(re.compile("/teachers/submission-deviations/"))
    navigate_to_default_course(page)

    sidebar.get_by_role("link", name="All submissions").click()
    expect(page).to_have_url(re.compile("/teachers/all-submissions/"))
    