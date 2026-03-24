from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_teacher_permissions(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "teacher", "teacher")
    navigate_to_default_course(page)

    left_sidebar = page.locator("#main-course-menu")
    expect(left_sidebar).to_contain_text("Course staff")

    expected_links = [
    "Participants",
    "Groups",
    "All results",
    "Visualizations",
    "Pseudonymize",
    "Edit news",
    "Edit course",
    "Deadline deviations",
    "Submission deviations",
    "All submissions",
    ]

    for link in expected_links:
        expect(left_sidebar.get_by_role("link", name=link)).to_be_visible()

    left_sidebar.get_by_role("link", name="Edit course").click()
    expect(page).to_have_title("Edit course | Def. Course | A+")


def test_assistant_permissions(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "assistant", "assistant")
    navigate_to_default_course(page)

    left_sidebar = page.locator("#main-course-menu")
    expect(left_sidebar).to_contain_text("Course staff")

    expected_links = [
        "Participants",
        "Groups",
        "Pseudonymize",
    ]

    unexpected_links = [
        "All results",
        "Visualizations",
        "Edit news",
        "Edit course",
        "Deadline deviations",
        "Submission deviations",
        "All submissions",
    ]

    for link in expected_links:
        expect(left_sidebar.get_by_role("link", name=link)).to_be_visible()

    for link in unexpected_links:
        expect(left_sidebar.get_by_role("link", name=link)).not_to_be_visible()


def test_student_permissions(page: Page):
    page.goto("http://localhost:8000/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)

    left_sidebar = page.locator("#main-course-menu")
    expect(left_sidebar).not_to_contain_text("Course staff")

    unexpected_links = [
        "Participants",
        "Groups",
        "All results",
        "Visualizations",
        "Pseudonymize",
        "Edit news",
        "Edit course",
        "Deadline deviations",
        "Submission deviations",
        "All submissions",
    ]

    for link in unexpected_links:
        expect(left_sidebar.get_by_role("link", name=link)).not_to_be_visible()
