"""
app_helper_generator.py
========================
Reads selector_map.json (built from any recorded_flow.py) and generates
a Python helper library of named _app_* functions that the LLM calls
instead of writing raw selectors.

Swap in a new recorded_flow.py for any application and this module
produces the correct helpers automatically — no hardcoding.
"""

import re
import textwrap
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Indentation helper
# ─────────────────────────────────────────────────────────────────────────────

def _indent(code: str, spaces: int = 4) -> str:
    """Indent every non-empty line of code by the given number of spaces."""
    pad = " " * spaces
    return "\n".join(pad + l if l.strip() else l for l in code.splitlines())


# ─────────────────────────────────────────────────────────────────────────────
# Statement builder – one Playwright line per action
# ─────────────────────────────────────────────────────────────────────────────

def _action_text(action: Dict) -> str:
    """Return the best available human-visible text for an action."""
    return action.get("name") or action.get("text") or ""


def _stmt_for_action(action: Dict) -> str:
    """
    Return a Playwright statement (no indentation) for one recorded action.
    Ends with a page.wait_for_load_state call so callers don't need to add one.
    """
    kind     = action.get("kind", "other")
    act      = action.get("action", "click")
    selector = action.get("selector", "")
    filt     = action.get("filter", "")
    role     = action.get("role", "")
    name     = _action_text(action)
    value    = action.get("value", "")

    wait = 'page.wait_for_load_state("networkidle")'

    if kind == "filter_chain":
        filt_esc = re.sub(r'(["\\])', r'\\\1', filt)
        return (
            f'page.locator("{selector}").filter(\n'
            f'    has_text=re.compile(r"^{filt_esc}$")\n'
            f').first.click()\n'
            f'{wait}'
        )

    if kind == "role":
        if act == "fill":
            return f'page.get_by_role("{role}", name="{name}").fill("{value}")\n{wait}'
        if act == "press":
            return f'page.get_by_role("{role}", name="{name}").press("{value}")\n{wait}'
        return f'page.get_by_role("{role}", name="{name}").click()\n{wait}'

    if kind == "text":
        exact = action.get("exact", False)
        if exact:
            return f'page.get_by_text("{name}", exact=True).click()\n{wait}'
        return f'page.get_by_text("{name}").click()\n{wait}'

    if kind == "fill_input":
        return (
            f'page.locator("{selector}").click()\n'
            f'page.locator("{selector}").fill("{value}")\n'
            f'{wait}'
        )

    if kind in ("locator", "css"):
        if act == "fill":
            return f'page.locator("{selector}").fill("{value}")\n{wait}'
        return f'page.locator("{selector}").click()\n{wait}'

    return f"# {action.get('raw', '')}"


# ─────────────────────────────────────────────────────────────────────────────
# Per-category helper builders
# ─────────────────────────────────────────────────────────────────────────────

def _fn(name: str, args: str, doc: str, body: str) -> str:
    """Assemble a properly-indented Python function string."""
    doc_lines = textwrap.fill(doc, 72)
    body_indented = _indent(body, 4)
    return f'def {name}({args}):\n    """{doc_lines}"""\n{body_indented}\n'


def _build_navigation_helpers(actions: List[Dict]) -> str:
    if not actions:
        return ""
    link_names = []
    for a in actions:
        if a.get("kind") == "role" and a.get("role") == "link":
            n = a.get("name", "")
            if n and n not in link_names:
                link_names.append(n)
    known = ", ".join(link_names)
    body = (
        'page.get_by_role("link", name=section).click()\n'
        'page.wait_for_load_state("networkidle")'
    )
    return _fn(
        "_app_navigate_to", 'page, section: str',
        f"Navigate to a section by its link name. Known sections: {known}",
        body,
    )


def _build_filter_helpers(actions: List[Dict]) -> str:
    """
    Build named helpers only for real filter-panel navigation actions.
    Filter chains that look like modal/content interactions (Preview,
    Remove Reference, Select All, numeric labels) are skipped.
    """
    if not actions:
        return ""

    # Only keep actions whose filter text looks like a panel section name:
    # - Short (≤30 chars), no digits-only, not obviously a content label
    SKIP_PATTERNS = re.compile(
        r"^\d+$|^Preview$|^Remove Reference$|^Select All$|^Close$|^Cancel$",
        re.IGNORECASE,
    )

    panel_actions = [
        a for a in actions
        if a.get("kind") == "filter_chain"
        and a.get("filter", "")
        and not SKIP_PATTERNS.match(a.get("filter", ""))
    ]

    if not panel_actions:
        return ""

    def _fallback_filter_chain(action: Dict) -> str:
        filt_esc = re.sub(r'(["\\])', r'\\\1', action.get("filter", ""))
        selector = action.get("selector", "")
        return (
            f'page.locator("{selector}").filter('
            f'has_text=re.compile(r"^{filt_esc}$", re.IGNORECASE)'
            f').first.click()'
        )

    def _robust_click_body(label: str, roles: List[str], fallback_line: str) -> str:
        roles_list = ", ".join(f'"{r}"' for r in roles)
        return (
            "clicked = False\n"
            f"for _role in [{roles_list}]:\n"
            "    try:\n"
            f"        loc = page.get_by_role(_role, name=re.compile(r\"^{label}$\", re.IGNORECASE)).first\n"
            "        if loc.is_visible(timeout=2000):\n"
            "            loc.click()\n"
            "            clicked = True\n"
            "            break\n"
            "    except Exception:\n"
            "        pass\n"
            "if not clicked:\n"
            "    try:\n"
            f"        page.get_by_text(\"{label}\", exact=True).first.click()\n"
            "        clicked = True\n"
            "    except Exception:\n"
            "        pass\n"
            "if not clicked:\n"
            f"    {fallback_line}\n"
            "page.wait_for_load_state(\"networkidle\")"
        )

    parts = []
    used_names: set = set()
    nav_fn_calls = []

    for a in panel_actions:
        filt = a.get("filter", "")
        label = re.sub(r"[^a-z0-9]", "_", filt.lower()).strip("_")[:30]
        label = re.sub(r"_+", "_", label)
        fn_name = f"_app_open_{label}_section"
        if fn_name in used_names:
            continue
        used_names.add(fn_name)
        nav_fn_calls.append(fn_name)

        filt_lower = filt.strip().lower()
        if filt_lower in ("filters", "tags"):
            roles = ["tab", "link", "button"] if filt_lower == "filters" else ["link", "tab", "button"]
            body = _robust_click_body(filt, roles, _fallback_filter_chain(a))
        else:
            body = _stmt_for_action(a)
        parts.append(_fn(
            fn_name, "page",
            f"Open/expand the '{filt}' section. Source: {a.get('raw', '')}",
            body,
        ))

    # Convenience wrapper that calls the two most likely setup functions
    primary_calls = "\n".join(f"{fn}(page)" for fn in nav_fn_calls[:2]) or "pass"
    parts.append(_fn(
        "_app_open_filter_panel", "page",
        "Open the filter panel and expand the default section. "
        "Calls the individual filter helpers generated from the recording.",
        primary_calls,
    ))

    return "\n".join(parts)


def _build_search_helpers(actions: List[Dict]) -> str:
    if not actions:
        return ""

    parts = []
    seen: set = set()

    # Generic search input helper
    fill_actions = [a for a in actions if a.get("action") == "fill" and a.get("kind") == "fill_input"]
    if fill_actions:
        a = fill_actions[0]
        sel = a.get("selector", "")
        body = (
            f'page.locator("{sel}").click()\n'
            f'page.locator("{sel}").fill(query)\n'
            f'page.wait_for_load_state("networkidle")'
        )
        parts.append(_fn(
            "_app_search", "page, query: str",
            f"Type a search/filter query. Source selector: {sel}",
            body,
        ))

    # Operator buttons
    op_actions = [
        a for a in actions
        if a.get("kind") == "text" and _action_text(a).upper() in ("OR", "AND", "NOT")
    ]
    for a in op_actions:
        op  = _action_text(a) or "OR"
        op = op.upper()
        fn  = f"_app_apply_{op.lower()}_operator"
        if fn in seen:
            continue
        seen.add(fn)
        body = (
            f'clicked = False\n'
            f'if nth == 0:\n'
            f'    try:\n'
            f'        loc = page.get_by_role("button", name=re.compile(r"^{op}$", re.IGNORECASE)).first\n'
            f'        if loc.is_visible(timeout=2000):\n'
            f'            loc.click()\n'
            f'            clicked = True\n'
            f'    except Exception:\n'
            f'        pass\n'
            f'    if not clicked:\n'
            f'        page.get_by_text("{op}", exact=True).first.click()\n'
            f'else:\n'
            f'    page.get_by_text("{op}").nth(nth).click()\n'
            f'page.wait_for_load_state("networkidle")'
        )
        parts.append(_fn(
            fn, "page, nth: int = 0",
            f"Click the {op} operator button. nth=0 for first, nth=N for subsequent.",
            body,
        ))

    return "\n".join(parts)


def _build_tag_helpers(actions: List[Dict]) -> str:
    if not actions:
        return ""

    samples = []
    for a in actions[:5]:
        n = _action_text(a)
        core = re.sub(r"\d+$", "", n).strip()
        if core and core not in samples:
            samples.append(core)
    sample_str = ", ".join(samples)

    tag_locator_body = (
        'pattern = re.compile(rf"^{re.escape(tag_name)}(\\d+)?$", re.IGNORECASE)\n'
        'loc = page.locator("a,div,span,li,button").filter(has_text=pattern).first\n'
        'try:\n'
        '    if loc.is_visible(timeout=1000):\n'
        '        return loc\n'
        'except Exception:\n'
        '    pass\n'
        'return page.get_by_text(tag_name, exact=True).first'
    )
    is_selected_body = (
        'loc = _app_tag_locator(page, tag_name)\n'
        'try:\n'
        '    cls = (loc.get_attribute("class") or "").lower()\n'
        '    if "selected" in cls or "active" in cls:\n'
        '        return True\n'
        '    if (loc.get_attribute("aria-selected") == "true" or loc.get_attribute("aria-pressed") == "true"):\n'
        '        return True\n'
        'except Exception:\n'
        '    pass\n'
        'return False'
    )
    click_body = (
        'loc = _app_tag_locator(page, tag_name)\n'
        'try:\n'
        '    loc.click()\n'
        'except Exception:\n'
        '    try:\n'
        '        page.get_by_text(re.compile(rf"^{re.escape(tag_name)}\\d+$")).first.click()\n'
        '    except Exception:\n'
        '        page.get_by_text(tag_name, exact=True).first.click()\n'
        'page.wait_for_load_state("networkidle")'
    )
    tags_body = (
        'try:\n'
        '    tags = []\n'
        '    for tag in ["a", "div", "span", "li"]:\n'
        '        elems = page.locator(tag).filter(\n'
        '            has_text=re.compile(r"^\\w[\\w\\s]+\\d+$")\n'
        '        ).all()\n'
        '        for e in elems:\n'
        '            t = re.sub(r"\\d+$", "", e.inner_text(timeout=2000).strip()).strip()\n'
        '            if t and t not in tags:\n'
        '                tags.append(t)\n'
        '        if tags:\n'
        '            break\n'
        '    if not tags:\n'
        '        sel = page.locator("*[aria-selected=\'true\'], *[aria-pressed=\'true\'], .selected, .active").all()\n'
        '        for e in sel:\n'
        '            t = (e.inner_text(timeout=2000) or \"\").strip()\n'
        '            if t:\n'
        '                t = re.sub(r"\\d+$", "", t).strip()\n'
        '                if t and t not in tags and len(t) <= 30:\n'
        '                    tags.append(t)\n'
        '    return tags\n'
        'except Exception:\n'
        '    return []'
    )
    count_body = (
        'try:\n'
        '    text = page.get_by_text(\n'
        '        re.compile(r"Total \\d+ items")\n'
        '    ).first.inner_text(timeout=5000)\n'
        '    m = re.search(r"(\\d+)", text)\n'
        '    return int(m.group(1)) if m else 0\n'
        'except Exception:\n'
        '    return 0'
    )
    assert_body = (
        'if expected is None and expected_count is not None:\n'
        '    expected = expected_count\n'
        'actual = _app_get_result_count(page)\n'
        'assert actual == expected, (\n'
        '    f"{msg or \'Result count\'}: expected {expected}, got {actual}"\n'
        ')'
    )

    return "\n".join([
        _fn(
            "_app_tag_locator", "page, tag_name: str",
            "Return a locator for a tag item by name (count suffix optional).",
            tag_locator_body,
        ),
        _fn(
            "_app_is_tag_selected", "page, tag_name: str",
            "Return True if the tag appears selected/active.",
            is_selected_body,
        ),
        _fn(
            "_app_click_tag", "page, tag_name: str",
            f"Click a tag filter item by name only (count suffix is ignored). "
            f"Tags display as name+count e.g. 'toys59'. "
            f"Sample names from recording: {sample_str}",
            click_body,
        ),
        _fn("_app_get_visible_tags", "page",
            "Return list of tag names (without count) visible in the tag panel.",
            tags_body),
        _fn("_app_get_result_count", "page",
            "Read the total result count from a 'Total N items' label. Returns 0 if not found.",
            count_body),
        _fn("_app_assert_result_count", "page, expected: int = None, msg: str = '', expected_count: int = None",
            "Assert the total result count equals expected.",
            assert_body),
    ])


def _build_asset_helpers(actions: List[Dict]) -> str:
    if not actions:
        return ""

    parts = []

    thumb = next((a for a in actions if a.get("role") == "img" and "thumb" in a.get("name", "")), None)
    if thumb:
        body = (
            'page.get_by_role("img", name="thumb").nth(index).click()\n'
            'page.wait_for_load_state("networkidle")'
        )
        parts.append(_fn("_app_open_asset", "page, index: int = 0",
                         "Click a thumbnail to open an asset. index=0 for the first.",
                         body))

    tab_names = [a.get("name", "") for a in actions if a.get("role") == "tab"]
    if tab_names:
        body = (
            'page.get_by_role("tab", name=tab_name).click()\n'
            'page.wait_for_load_state("networkidle")'
        )
        parts.append(_fn("_app_click_asset_tab", 'page, tab_name: str',
                         f"Click an asset detail tab by name. Known tabs: {', '.join(tab_names)}",
                         body))

    return "\n".join(parts)


def _build_system_helpers(actions: List[Dict]) -> str:
    if not actions:
        return ""
    parts = []
    seen: set = set()
    for a in actions:
        n  = _action_text(a)
        fn = f"_app_{re.sub(r'[^a-z0-9]', '_', n.lower()).strip('_')}"
        fn = re.sub(r"_+", "_", fn)
        if fn in seen or not n:
            continue
        seen.add(fn)
        body = _stmt_for_action(a)
        parts.append(_fn(fn, "page", n, body))
    return "\n".join(parts)


def _build_action_btn_helpers(actions: List[Dict]) -> str:
    if not actions:
        return ""
    SKIP = {"login", "sign in", "log in", "sign up", "close", "cancel",
            "ok", "yes", "no", "submit"}
    parts = []
    seen: set = set()
    for a in actions:
        n  = _action_text(a)
        if not n or n.lower() in SKIP:
            continue
        fn = f"_app_{re.sub(r'[^a-z0-9]', '_', n.lower()).strip('_')}"
        fn = re.sub(r"_+", "_", fn)
        if fn in seen:
            continue
        seen.add(fn)
        body = _stmt_for_action(a)
        parts.append(_fn(fn, "page", f"Click the {n} button.", body))
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Main public API
# ─────────────────────────────────────────────────────────────────────────────

class AppHelperGenerator:
    """
    Generates a Python helper library from a selector_map.json built by
    selector_map_loader.  Works for any recorded application.

    Usage:
        gen = AppHelperGenerator(selector_map)
        code  = gen.generate()   # inject into every test script
        menu  = gen.menu()       # inject into LLM system prompt
    """

    def __init__(self, selector_map: Dict):
        self._map    = selector_map
        self._by_cat: Dict[str, List[Dict]] = selector_map.get("by_category", {})

    def generate(self) -> str:
        """Return a complete Python source block of _app_* helper functions."""
        header = (
            "# ── App Helper Library (auto-generated from recorded_flow.py) ────────\n"
            "# Regenerated automatically whenever recorded_flow.py changes.\n"
            "# The LLM calls these helpers — it never writes raw selectors.\n"
        )
        footer = "# ── End App Helper Library ───────────────────────────────────────────"

        builders = [
            _build_navigation_helpers(self._by_cat.get("navigation", [])),
            _build_filter_helpers(    self._by_cat.get("filter",     [])),
            _build_search_helpers(    self._by_cat.get("search",     [])),
            _build_tag_helpers(       self._by_cat.get("tag",        [])),
            _build_asset_helpers(     self._by_cat.get("asset",      [])),
            _build_system_helpers(    self._by_cat.get("system",     [])),
            _build_action_btn_helpers(self._by_cat.get("action_btn", [])),
        ]

        blocks = [b.strip() for b in builders if b and b.strip()]
        return "\n\n".join([header] + blocks + [footer])

    def menu(self) -> str:
        """Compact reference for the LLM system prompt."""
        lines = [
            "AVAILABLE APP HELPERS — use ONLY these for app interactions.",
            "⛔  NEVER write raw page.locator(), page.get_by_text(), page.get_by_role()",
            "    for app UI elements — call the helpers below instead.\n",
        ]

        specs = [
            ("navigation", "Navigation",          ['_app_navigate_to(page, "SectionName")']),
            ("filter",     "Filter Panel",         None),
            ("search",     "Search / Operators",   None),
            ("tag",        "Tags / Results",       [
                '_app_click_tag(page, "tag_name")   # name only — ignores count suffix',
                '_app_get_visible_tags(page)         # → list of tag names',
                '_app_get_result_count(page)         # → int',
                '_app_assert_result_count(page, N)',
            ]),
            ("asset",      "Assets",               [
                '_app_open_asset(page, index=0)',
                '_app_click_asset_tab(page, "TabName")',
            ]),
            ("system",     "Utilities",            None),
            ("action_btn", "Action Buttons",       None),
        ]

        for cat, label, fixed_items in specs:
            actions = self._by_cat.get(cat, [])
            if not actions and not fixed_items:
                continue
            lines.append(f"  {label}:")

            if fixed_items:
                for item in fixed_items:
                    lines.append(f"    {item}")
            else:
                # Derive function names the same way the generators do
                if cat == "filter":
                    SKIP = re.compile(
                        r"^\d+$|^Preview$|^Remove Reference$|^Select All$|^Close$|^Cancel$",
                        re.IGNORECASE,
                    )
                    seen: set = set()
                    for a in actions:
                        f_ = a.get("filter", "")
                        if not f_ or SKIP.match(f_):
                            continue
                        lbl = re.sub(r"[^a-z0-9]", "_", f_.lower()).strip("_")[:30]
                        lbl = re.sub(r"_+", "_", lbl)
                        fn  = f"_app_open_{lbl}_section(page)"
                        if fn not in seen:
                            seen.add(fn)
                            lines.append(f"    {fn}")
                    lines.append("    _app_open_filter_panel(page)")
                elif cat == "search":
                    has_fill = any(a.get("kind") == "fill_input" for a in actions)
                    if has_fill:
                        lines.append('    _app_search(page, "query")')
                    for a in actions:
                        op = _action_text(a).upper()
                        if op in ("OR", "AND", "NOT"):
                            lines.append(f'    _app_apply_{op.lower()}_operator(page, nth=0)')
                elif cat == "system":
                    seen2: set = set()
                    for a in actions:
                        n  = _action_text(a)
                        fn = f"_app_{re.sub(r'[^a-z0-9]', '_', n.lower()).strip('_')}(page)"
                        fn = re.sub(r"_+", "_", fn)
                        if fn not in seen2 and n:
                            seen2.add(fn)
                            lines.append(f"    {fn}")
                elif cat == "action_btn":
                    SKIP_BTN = {"login", "sign in", "log in", "close", "cancel", "ok"}
                    seen3: set = set()
                    for a in actions[:8]:
                        n  = _action_text(a)
                        if not n or n.lower() in SKIP_BTN:
                            continue
                        fn = f"_app_{re.sub(r'[^a-z0-9]', '_', n.lower()).strip('_')}(page)"
                        fn = re.sub(r"_+", "_", fn)
                        if fn not in seen3:
                            seen3.add(fn)
                            lines.append(f"    {fn}")
            lines.append("")

        return "\n".join(lines)

    def has_helpers(self) -> bool:
        return bool(
            self._by_cat.get("filter") or
            self._by_cat.get("navigation") or
            self._by_cat.get("tag") or
            self._by_cat.get("search")
        )


    def known_tag_names(self) -> list:
        """
        Return a list of real tag names extracted from the recording.
        These are text-click actions whose labels end in digits (e.g. 'toys59').
        The count suffix is stripped so only the name is returned.

        Filters out:
          - Items whose name looks like a workflow/document title (>3 words)
          - Items with very high counts (likely total counters, not tag items)
          - Short fragments like "EN" that appear to be incomplete
        """
        import re as _re
        tags = []
        seen = set()
        for a in self._by_cat.get("tag", []):
            raw_name = _action_text(a)
            core = _re.sub(r"\d+$", "", raw_name).strip()
            # Skip empty, too-long (workflow titles), or multi-word phrases with 4+ words
            if not core or len(core) > 30:
                continue
            # Skip very short fragments like "EN"
            if len(core) < 3 and core.isupper():
                continue
            word_count = len(core.split())
            if word_count > 3:
                continue
            # Skip if the original name has a very large count (>999 likely a total, not a tag)
            digits = _re.search(r"(\d+)$", raw_name)
            if digits and int(digits.group(1)) > 999:
                continue
            if core not in seen:
                seen.add(core)
                tags.append(core)
        return tags

    def known_fn_names(self) -> set:
        """
        Return the set of _app_* function names that will actually be generated.
        Used by _clean_body to detect and reject hallucinated helper calls.
        """
        names = {
            "_app_navigate_to",
            "_app_open_filter_panel",
            "_app_search",
            "_app_tag_locator",
            "_app_is_tag_selected",
            "_app_click_tag",
            "_app_get_visible_tags",
            "_app_get_result_count",
            "_app_assert_result_count",
            "_app_open_asset",
            "_app_click_asset_tab",
            "_app_clear_search",
        }
        # Add dynamically generated names
        SKIP = re.compile(
            r"^\d+$|^Preview$|^Remove Reference$|^Select All$|^Close$|^Cancel$",
            re.IGNORECASE,
        )
        for a in self._by_cat.get("filter", []):
            f_ = a.get("filter", "")
            if f_ and not SKIP.match(f_):
                lbl = re.sub(r"[^a-z0-9]", "_", f_.lower()).strip("_")[:30]
                lbl = re.sub(r"_+", "_", lbl)
                names.add(f"_app_open_{lbl}_section")
        for a in self._by_cat.get("search", []):
            op = _action_text(a).upper()
            if op in ("OR", "AND", "NOT"):
                names.add(f"_app_apply_{op.lower()}_operator")
        for a in self._by_cat.get("system", []):
            n = _action_text(a)
            fn = f"_app_{re.sub(r'[^a-z0-9]', '_', n.lower()).strip('_')}"
            fn = re.sub(r"_+", "_", fn)
            if n:
                names.add(fn)
        for a in self._by_cat.get("action_btn", []):
            n = _action_text(a)
            SKIP_BTN = {"login", "sign in", "log in", "close", "cancel", "ok"}
            if n and n.lower() not in SKIP_BTN:
                fn = f"_app_{re.sub(r'[^a-z0-9]', '_', n.lower()).strip('_')}"
                fn = re.sub(r"_+", "_", fn)
                names.add(fn)
        return names
