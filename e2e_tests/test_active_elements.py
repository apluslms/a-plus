import re

from playwright.sync_api import Page, expect

from e2e_tests.helpers import login, navigate_to_default_course

# A tiny valid 1x1 red PNG, base64-encoded.
TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"


def open_active_elements_chapter(page: Page):
    login(page, "student", "student")
    navigate_to_default_course(page)
    page.get_by_role("link", name="16.1 Active elements").first.click()
    # The minimal active element: an input that echoes its value into the output.
    output = page.locator("#chapter-exercise-1")
    expect(output.locator(".ae_result")).to_be_attached()
    return output


def test_output_renders_input_as_literal_text(page: Page) -> None:
    output = open_active_elements_chapter(page)

    # The echo grader returns the input as-is, so markup-looking input must
    # stay literal text in the output and must not create any elements.
    page.locator("#min_input_input_id").fill("<ok> a < b")
    page.locator("#min_input").get_by_role("button", name="Submit").click()

    result = output.locator(".ae_result")
    expect(result).to_contain_text("<ok> a < b", timeout=65000)

    # The literal text must not have been interpreted as HTML: no <ok> or <b>
    # elements may exist inside the output, and the result must contain only
    # text nodes.
    expect(result.locator("ok")).to_have_count(0)
    expect(result.locator("b")).to_have_count(0)
    child_elements = page.evaluate(
        """(selector) => {
            const result = document.querySelector(selector);
            return Array.from(result.children).length;
        }""",
        "#chapter-exercise-1 .ae_result",
    )
    assert child_elements == 0


def test_image_output_renders_base64_png(page: Page) -> None:
    output = open_active_elements_chapter(page)

    # There is no image-type active element in the default course, so drive
    # the output rendering directly with the same feedback structure that the
    # grader produces for image outputs.
    page.evaluate(
        """([selector, base64]) => {
            const element = document.querySelector(selector);
            element.setAttribute('data-type', 'image');
            const exercise = $(element).data('plugin_aplusExercise');
            exercise.updateOutput('<div id="feedback"><pre>' + base64 + '</pre></div>');
        }""",
        ["#chapter-exercise-1", TINY_PNG_BASE64],
    )

    img = output.locator(".ae_result img")
    expect(img).to_have_count(1)
    expect(img).to_have_attribute("src", re.compile(r"^data:image/png;base64, "))
    # The image must actually decode and render, i.e. the base64 was valid.
    expect(img).to_have_js_property("naturalWidth", 1)
