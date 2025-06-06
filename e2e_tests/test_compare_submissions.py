from playwright.sync_api import Page, expect
from e2e_tests.helpers import upload_submission, login, logout, navigate_to_default_course, File


def test_compare_submissions(page: Page) -> None:
    ASSISTANT_FEEDBACK_TEXT = "ASSISTANT_FEEDBACK"
    FEEDBACK_TEXT = "FEEDBACK"
    POINTS = "5"

    page.goto("http://localhost:8000/?hl=en")
    chapter_name = "6.3 Exercises with Python"
    exercise_name = "#chapter-exercise-6"
    green = "rgb(212, 237, 218)"
    red = "rgb(248, 215, 218)"
    login(page, "student", "student")
    navigate_to_default_course(page)
    upload_submission(
        page,
        chapter_name=chapter_name,
        exercise_name=exercise_name,
        files=(File("wallet.py"), File("wallet_program.py"))
    )
    upload_submission(
        page,
        chapter_name=chapter_name,
        exercise_name=exercise_name,
        files=(File("wallet2.py", "wallet.py"), File(
            "wallet_program2.py", "wallet_program.py"))
    )
    logout(page)
    login(page, "teacher", "teacher")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Course materials").click()
    first_link = page.get_by_role("link", name="6.3 Exercises with Python").first
    first_link.click()
    page.get_by_label("6.3.6 Wallet").get_by_role(
        "button", name="View all submissions").click()
    page.locator("#submission-2").get_by_role("link", name="Inspect").click()

    def assert_line(filename: str, line_number: int, text: str, color: str):
        line = page.get_by_test_id(f"{filename}-line-{line_number}")
        expect(line).to_contain_text(text)
        expect(line).to_have_css("background-color", color)

    page.get_by_role("link", name="Compare to model answer").click()
    expect(page.get_by_role("main")).to_contain_text(
        "Comparing to the model solution.")
    assert_line("wallet2.py", 3, "# Added line in wallet.py2.", green)
    assert_line("wallet2.py", 6, "self.__balance = balance", red)

    page.get_by_role("link", name="Compare", exact=True).click()
    expect(page.get_by_role("main")).to_contain_text("Comparing to submission")
    assert_line("wallet2.py", 3, "# Added line in wallet.py.", red)
    assert_line("wallet2.py", 4, "# Added line in wallet.py2.", green)
    page.get_by_role("tab", name="wallet_program2.py").click()
    assert_line("wallet_program2.py", 10,
                "# Modified line in wallet_program.py.", red)
    assert_line("wallet_program2.py", 11,
                "# Modified line in wallet_program2.py.", green)

    # Assess exercise manually
    page.get_by_role("button", name="Assess manually").click()
    page.get_by_placeholder("Staff feedback").fill(ASSISTANT_FEEDBACK_TEXT)
    page.get_by_role("button", name="Grader feedback").click()
    page.get_by_placeholder("Grader feedback").fill(FEEDBACK_TEXT)
    page.get_by_label("Points").fill(POINTS)
    page.get_by_role("button", name="Submit").click()
    expect(page.locator('.site-message')).to_contain_text(
        "The review was saved successfully and the submitters were notified.")

    page.goto(
        "http://localhost:8000/def/current/programming_exercises/graderutils" +
        "/programming_exercises_graderutils_iotester_exercise2/submissions/2/inspect/?compare_to=invalid"
    )
    expect(page.get_by_role("main")).to_contain_text(
        "The file you are attempting to compare to was not found.")

    logout(page)

    # Check that student receives the correct assessment and a notification of it
    login(page, "student", "student")
    notification_menu = page.get_by_role("button", name="new notification")
    expect(notification_menu).to_be_visible()
    notification_menu.click()

    # Click on the first item on the notification menu
    page.locator("#notification-alert").get_by_role(
        "link",
        name="DEF000 6.3 Exercises with Python grader utils, 6.3.6 Wallet"
    ).click()

    # Check that we have the correct feedback
    expect(page.locator("#exercise-all")).to_contain_text(ASSISTANT_FEEDBACK_TEXT)
    expect(page.locator("#exercise-all")).to_contain_text(FEEDBACK_TEXT)
    expect(page.locator("td.points-badge")).to_contain_text(POINTS + " / 100")