import re
from playwright.sync_api import Page, expect
from e2e_tests.helpers import navigate_to_default_course, login


def test_homepage(page: Page):
    page.goto("http://localhost:8010/?hl=en")
    expect(page).to_have_title(re.compile("A+"))

    login(page, "student", "student")
    navigate_to_default_course(page)

    #test top navbar

    top_navbar = page.get_by_role("navigation", name="Main")
    expect(top_navbar).to_be_visible()

    expect(top_navbar.get_by_role("link", name="A+", exact=True)).to_be_visible()
    expect(top_navbar.locator("#bd-theme")).to_be_visible()
    expect(top_navbar.get_by_test_id("user-menu")).to_be_visible()

    course_toggle = top_navbar.locator("a.dropdown-toggle").filter(has_text="DEF000")
    expect(course_toggle).to_be_visible()
    course_toggle.first.click()
    expect(page.locator("#courseDropdownMenu")).to_be_visible()
    expect(page.locator("#courseDropdownMenu").get_by_role("link", name="DEF000 Def. Course: Current")).to_be_visible()

    top_navbar.locator("#bd-theme").click()
    expect(top_navbar.get_by_role("button", name="Dark (experimental)")).to_be_visible()

    top_navbar.get_by_test_id("user-menu").click()
    expect(page.get_by_role("link", name="Account")).to_be_visible()
    expect(page.get_by_role("button", name="Log out")).to_be_visible()

    #test main content
    #(don't test first module as its name is changed in test_edit_module_page.py)

    top_level_titles = [
        "2. Set up your environment",
        "3. RST Guide",
        "4. Style Aplus courses",
        "5. Questionnaires",
        "6. Programming exercises",
        "7. Acos server",
        "8. Jutut service for feedback and messaging",
        "9. Interactive code blocks",
        "10. Converting an old course for current A+",
        "11. External LTI (Learning Tools Interoperability) exercises and services",
        "12. Rubyric",
        "13. Course administration",
        "14. Languages",
        "15. Moodle Astra plugin",
        "16. Active elements",
        "17. Point of Interest",
        "18. Adding Sphinx extensions",
    ]
    main_toc = page.locator("ul.toc").first
    for title in top_level_titles:
        expect(main_toc.get_by_role("link", name=title, exact=True)).to_be_visible()

    #test left sidebar course menu, make sure that only links visible to students are present

    course_menu = page.locator("#main-course-menu")
    expected_course_menu_link_names_core = [
        "DEF000",
        "Course materials",
        "Your points",
    ]
    expected_course_menu_link_names_with_local_services = [
        "DEF000",
        "Course materials",
        "Your points",
        "Rubyric",
        "Radar",
        "Jutut",
    ]
    actual_course_menu_link_names = course_menu.locator("a.nav-link .course-menu-label").evaluate_all(
        "elements => elements.map((el) => el.textContent.trim())"
    )
    assert actual_course_menu_link_names in [
        expected_course_menu_link_names_core,
        expected_course_menu_link_names_with_local_services,
    ]

    expect(page.get_by_role("heading", name="A+ Manual")).to_be_visible()
