import re

from playwright.sync_api import Page, expect

from e2e_tests.helpers import login, navigate_to_default_course

# Matches one personalized points goal block (template-rendered or DOM-built)
# inside the tooltip markup.
GOAL_BLOCK_REGEXP = r"<span class=[\"']personalized-points-full-text[^>]*>[\s\S]*?</span>\s*</span>"


def open_goal_modal(page: Page) -> None:
    page.locator("#progress-questionnaires").get_by_role("button", name="Points goal").click()
    expect(page.locator("#pointsGoalForm")).to_be_visible()


def save_goal(page: Page, value: str) -> None:
    page.get_by_label("Input personalized goal as").fill(value)
    page.get_by_role("button", name="Save").click()
    # The alert is rendered hidden in the modal, so to_contain_text alone
    # would pass before the save request completes. Wait for visibility:
    # the alert is shown only after the tooltip has been updated.
    expect(page.locator("#success-alert")).to_be_visible()
    expect(page.locator("#success-alert")).to_contain_text("Successfully set personalized points goal")
    page.get_by_role("button", name="Close", exact=True).click()


def tooltip_markup(page: Page) -> str:
    return page.evaluate(
        "document.querySelector('#progress-questionnaires .progress')?.getAttribute('data-bs-original-title')"
    ) or ""


def wait_for_tooltip_init(page: Page) -> None:
    # Bootstrap moves the title attribute to data-bs-original-title during
    # tooltip initialization; wait for that before reading the markup.
    page.wait_for_function(
        "document.querySelector('#progress-questionnaires .progress')?.hasAttribute('data-bs-original-title')"
    )


def count_goal_blocks(page: Page) -> int:
    return len(re.findall(GOAL_BLOCK_REGEXP, tooltip_markup(page)))


def has_goal_value(page: Page, value: str) -> bool:
    # The value is rendered without surrounding whitespace in the DOM-built
    # block but on its own indented line in the template-rendered block, so
    # the check must tolerate whitespace.
    return re.search(r">\s*" + re.escape(value) + r"\s*</span>", tooltip_markup(page)) is not None


def test_points_goal_set(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")
    login(page, "student", "student")

    navigate_to_default_course(page)
    page.get_by_role("link", name="Your points").click()
    open_goal_modal(page)
    save_goal(page, "50")

    # The tooltip markup must contain the goal block exactly once.
    assert count_goal_blocks(page) == 1
    assert "Points goal: <span class=\"personalized-points-text" in tooltip_markup(page)
    assert has_goal_value(page, "50")

    # The rendered tooltip shows the goal as visible text.
    page.locator("#progress-questionnaires .progress").hover()
    expect(page.locator(".tooltip")).to_contain_text("Points goal: 50")
    expect(page.locator("#goal-points"))


def test_points_goal_reached(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")
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
    open_goal_modal(page)
    save_goal(page, "30")
    progress_bar_locator = page.locator("#progress-questionnaires .progress > .aplus-progress-bar")
    expect(progress_bar_locator).\
        to_have_class("aplus-progress-bar aplus-progress-bar-striped aplus-progress-bar-primary")


def test_points_goal_update_and_reload(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Your points").click()

    # First save: the DOM-built block appears exactly once.
    open_goal_modal(page)
    save_goal(page, "50")
    assert count_goal_blocks(page) == 1
    assert has_goal_value(page, "50")

    # Second save without reload: the block is replaced, not duplicated.
    open_goal_modal(page)
    save_goal(page, "75")
    assert count_goal_blocks(page) == 1
    assert not has_goal_value(page, "50")
    assert has_goal_value(page, "75")

    # After a reload the block comes from the server-rendered template,
    # still exactly once, with the persisted value.
    page.reload()
    wait_for_tooltip_init(page)
    assert count_goal_blocks(page) == 1
    assert has_goal_value(page, "75")


def test_points_goal_delete(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Your points").click()

    open_goal_modal(page)
    save_goal(page, "50")
    assert count_goal_blocks(page) == 1

    # Remove the goal: the block disappears from the tooltip markup.
    open_goal_modal(page)
    page.get_by_role("button", name="Remove").click()
    # Wait for visibility: the alert is shown only after the tooltip has
    # been updated (see save_goal above for why to_contain_text is not enough).
    expect(page.locator("#remove-success-alert")).to_be_visible()
    expect(page.locator("#remove-success-alert")).to_contain_text(
        "Successfully removed personalized points goal")
    page.get_by_role("button", name="Close", exact=True).click()

    assert count_goal_blocks(page) == 0
    assert "personalized-points-full-text" not in tooltip_markup(page)


def test_points_goal_label_with_metacharacters_stays_literal(page: Page) -> None:
    page.goto("http://localhost:8010/?hl=en")
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="Your points").click()

    open_goal_modal(page)
    # Simulate a translation whose label contains HTML metacharacters. The
    # label must be inserted as text: the built block must contain it
    # entity-escaped, so the rendered tooltip shows it literally instead of
    # interpreting it as markup.
    label = "Goal <b>bold</b> & \"quoted\""
    page.evaluate(
        """(label) => {
            // Set via jQuery's data API so the cached value the save handler
            // reads is overridden regardless of attribute caching.
            $('#pointsGoalForm').data('personalized-points-goal-tooltip-text', label);
        }""",
        label,
    )
    save_goal(page, "50")

    markup = tooltip_markup(page)
    assert count_goal_blocks(page) == 1
    # The label was inserted as a text node: < and & are entity-escaped in the
    # serialized block, so the tooltip renders them literally.
    assert "Goal &lt;b&gt;bold&lt;/b&gt; &amp; \"quoted\": <span" in markup
    # No real markup from the label may exist inside the block.
    assert "Goal <b>" not in markup
