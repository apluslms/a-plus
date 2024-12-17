from playwright.sync_api import Page, expect
from e2e_tests.helpers import upload_submission, login, logout, File, dismiss_cookie_notice


def test_compare_submissions(page: Page) -> None:
    chapter_name = "6.3 Exercises with Python"
    exercise_name = "#chapter-exercise-6"
    green = "rgb(212, 237, 218)"
    red = "rgb(248, 215, 218)"
    login(page, "student", "student")
    dismiss_cookie_notice(page)
    page.get_by_role("link", name="Def. Course Current DEF000 1.").click()
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
    login(page, "assistant", "assistant")
    page.get_by_role("link", name="Def. Course Current DEF000 1.").click()
    page.get_by_role("link", name="Course materials").click()
    page.get_by_role("link", name="6.3 Exercises with Python").first.click()
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

    page.goto(
        "http://localhost:8000/def/current/programming_exercises/graderutils" +
        "/programming_exercises_graderutils_iotester_exercise2/submissions/2/inspect/?compare_to=invalid"
    )
    expect(page.get_by_role("main")).to_contain_text(
        "The file you are attempting to compare to was not found.")
