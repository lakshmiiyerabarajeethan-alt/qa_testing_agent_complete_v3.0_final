# ── App Helper Library (auto-generated from recorded_flow.py) ────────
# Regenerated automatically whenever recorded_flow.py changes.
# The LLM calls these helpers — it never writes raw selectors.


def _app_navigate_to(page, section: str):
    """Navigate to a section by its link name. Known sections: Folders, Tag
Cloud, Workflows, Products, Analytics"""
    page.get_by_role("link", name=section).click()
    page.wait_for_load_state("networkidle")

def _app_open_filters_section(page):
    """Open/expand the 'Filters' section. Source: page.locator("#rc-tabs-0-tab-
filters div").filter(has_text=re.compile(r"^Filters$")).click()"""
    clicked = False
    for _role in ["tab", "link", "button"]:
        try:
            loc = page.get_by_role(_role, name=re.compile(r"^Filters$", re.IGNORECASE)).first
            if loc.is_visible(timeout=2000):
                loc.click()
                clicked = True
                break
        except Exception:
            pass
    if not clicked:
        try:
            page.get_by_text("Filters", exact=True).first.click()
            clicked = True
        except Exception:
            pass
    if not clicked:
        page.locator("#rc-tabs-0-tab-filters div").filter(has_text=re.compile(r"^Filters$", re.IGNORECASE)).first.click()
    page.wait_for_load_state("networkidle")

def _app_open_tags_section(page):
    """Open/expand the 'Tags' section. Source:
page.locator("a").filter(has_text="Tags").click()"""
    clicked = False
    for _role in ["link", "tab", "button"]:
        try:
            loc = page.get_by_role(_role, name=re.compile(r"^Tags$", re.IGNORECASE)).first
            if loc.is_visible(timeout=2000):
                loc.click()
                clicked = True
                break
        except Exception:
            pass
    if not clicked:
        try:
            page.get_by_text("Tags", exact=True).first.click()
            clicked = True
        except Exception:
            pass
    if not clicked:
        page.locator("a").filter(has_text=re.compile(r"^Tags$", re.IGNORECASE)).first.click()
    page.wait_for_load_state("networkidle")

def _app_open_filter_panel(page):
    """Open the filter panel and expand the default section. Calls the
individual filter helpers generated from the recording."""
    _app_open_filters_section(page)
    _app_open_tags_section(page)

def _app_search(page, query: str):
    """Type a search/filter query. Source selector: #rc_select_6"""
    page.locator("#rc_select_6").click()
    page.locator("#rc_select_6").fill(query)
    page.wait_for_load_state("networkidle")

def _app_apply_or_operator(page, nth: int = 0):
    """Click the OR operator button. nth=0 for first, nth=N for subsequent."""
    if nth == 0:
        page.get_by_text("OR", exact=True).click()
    else:
        page.get_by_text("OR").nth(nth).click()
    page.wait_for_load_state("networkidle")

def _app_click_tag(page, tag_name: str):
    """Click a tag filter item by name only (count suffix is ignored). Tags
display as name+count e.g. 'toys59'. Sample names from recording: Delete
Asset, Vehicles, Lakshmi, Mr Cuddles, EN"""
    page.get_by_text(re.compile(rf"^{re.escape(tag_name)}\d+$")).first.click()
    page.wait_for_load_state("networkidle")

def _app_get_visible_tags(page):
    """Return list of tag names (without count) visible in the tag panel."""
    try:
        elems = page.locator("a").filter(
            has_text=re.compile(r"^\w[\w\s]+\d+$")
        ).all()
        return [
            re.sub(r"\d+$", "", e.inner_text(timeout=2000).strip()).strip()
            for e in elems
        ]
    except Exception:
        return []

def _app_get_result_count(page):
    """Read the total result count from a 'Total N items' label. Returns 0 if
not found."""
    try:
        text = page.get_by_text(
            re.compile(r"Total \d+ items")
        ).first.inner_text(timeout=5000)
        m = re.search(r"(\d+)", text)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0

def _app_assert_result_count(page, expected: int, msg: str = ''):
    """Assert the total result count equals expected."""
    actual = _app_get_result_count(page)
    assert actual == expected, (
        f"{msg or 'Result count'}: expected {expected}, got {actual}"
    )

def _app_open_asset(page, index: int = 0):
    """Click a thumbnail to open an asset. index=0 for the first."""
    page.get_by_role("img", name="thumb").nth(index).click()
    page.wait_for_load_state("networkidle")

def _app_click_asset_tab(page, tab_name: str):
    """Click an asset detail tab by name. Known tabs: References, Folders"""
    page.get_by_role("tab", name=tab_name).click()
    page.wait_for_load_state("networkidle")

def _app_clear_search(page):
    """Clear Search"""
    page.get_by_text("Clear Search").click()
    page.wait_for_load_state("networkidle")

def _app_is_tag_selected(page, tag_name: str) -> bool:
    """Check if a tag is currently selected/active in the filter panel.
    Inspects CSS classes on the element and its parent for known active indicators.
    Falls back to True if the element is visible but class inspection fails,
    since the tests themselves decide whether absence is a failure."""
    ACTIVE_CLASSES = ("selected", "active", "checked", "current", "ant-tag-checkable-checked")
    try:
        loc = page.get_by_text(
            re.compile(rf"^{re.escape(tag_name)}\d*$")
        ).first
        # Check element's own class list
        classes = loc.evaluate("el => el.className || ''", timeout=3000)
        if any(c in classes.lower() for c in ACTIVE_CLASSES):
            return True
        # Check parent element classes (common pattern in Ant Design / similar libs)
        parent_classes = loc.evaluate(
            "el => el.parentElement ? (el.parentElement.className || '') : ''",
            timeout=3000,
        )
        if any(c in parent_classes.lower() for c in ACTIVE_CLASSES):
            return True
        # Check grandparent (some filter UIs wrap in two containers)
        gp_classes = loc.evaluate(
            "el => (el.parentElement && el.parentElement.parentElement) "
            "? (el.parentElement.parentElement.className || '') : ''",
            timeout=3000,
        )
        return any(c in gp_classes.lower() for c in ACTIVE_CLASSES)
    except Exception:
        return False

def _app_tag_locator(page, tag_name: str):
    """Return a Playwright locator for a tag element by name (trailing count digits ignored).
    Usage: _app_tag_locator(page, 'toys').click()"""
    return page.get_by_text(re.compile(rf"^{re.escape(tag_name)}\d*$")).first

# ── End App Helper Library ───────────────────────────────────────────