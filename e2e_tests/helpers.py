import os
from typing import List

from playwright.sync_api import Page, expect


assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class File:
    def __init__(self, name: str, label: str = None):
        self.name = name
        self.label = label if label else name


def login(page: Page, username: str, password: str):
    page.goto("http://localhost:8000/?hl=en")
    page.get_by_role("link", name="Log in").click()
    page.get_by_label("Username").click()
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").click()
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Log in").click()


def logout(page: Page):
    page.get_by_test_id('user-menu').click()
    page.get_by_role("link", name="Log out").click()


def upload_submission(page: Page, chapter_name: str, exercise_name: str, files: List[File]):
    page.get_by_label("Course").get_by_role(
        "link", name="Course materials").click()
    page.get_by_role("link", name=chapter_name).click()
    for file in files:
        page.get_by_label(file.label).set_input_files(os.path.join(assets_path, file.name))
    page.locator(exercise_name).get_by_role("button", name="Submit").click()
    expect(page.locator("#page-modal")
           ).to_contain_text("Total points:", timeout=10000)
    page.get_by_role("button", name="Close", exact=True).click()

def navigate_to_default_course(page: Page):
    # If not at the site root, navigate to it
    if page.url != "http://localhost:8000/?hl=en":
        page.goto("http://localhost:8000/?hl=en")

    # Navigate to the default course
    page.get_by_role("link", name="Def. Course Current DEF000 1.").click()
