from playwright.sync_api import Page, expect
from e2e_tests.helpers import login, logout


def test_teacher_list_access_rights(page: Page):

    page.goto("http://localhost:8000/?hl=en")
    if page.get_by_test_id('user-menu').is_visible():
        logout(page)
    page.goto("http://localhost:8000/accounts/teachers")

    alert = page.get_by_role("alert")
    message = "Unfortunately, you are not permitted to view this content"

    expect(alert).to_be_visible()
    expect(alert).to_contain_text(message)

    login(page, "student", "student")
    page.goto("http://localhost:8000/accounts/teachers")
    expect(alert).to_be_visible()
    expect(alert).to_contain_text(message)

    logout(page)
    login(page, "teacher", "teacher")
    page.goto("http://localhost:8000/accounts/teachers")
    expect(alert).to_be_visible()
    expect(alert).to_contain_text(message)

    logout(page)
    login(page, "admin", "admin")
    page.goto("http://localhost:8000/accounts/teachers")
    expect(alert).not_to_be_visible()
    expect(page).to_have_title("Teacher list | A+")


def test_teacher_list_content(page: Page):

    page.goto("http://localhost:8000/?hl=en")
    login(page, "admin", "admin")
    page.goto("http://localhost:8000/accounts/teachers")

    table = page.get_by_role("table")
    expect(table).to_be_visible()

    rows = table.locator("tbody tr")
    expect(rows).to_have_count(3)

    expected_first_three_cols = [ #there are 5 columns in total, validate first 3
        [
            "Terry Teacher",
            "teacher@localhost.invalid",
            "aplus-manual Aplus Manual: Main",
        ],
        [
            "Terry Teacher",
            "teacher@localhost.invalid",
            "test-course Test Course: Master",
        ],
        [
            "Terry Teacher",
            "teacher@localhost.invalid",
            "DEF000 Def. Course: Current",
        ],
    ]

    for i, expected_cells in enumerate(expected_first_three_cols):
        row_cells = rows.nth(i).locator("td")
        expect(row_cells).to_have_count(5)

        for j, expected_text in enumerate(expected_cells):
            expect(row_cells.nth(j)).to_contain_text(expected_text)
            expect(row_cells.nth(j)).to_contain_text(expected_text)