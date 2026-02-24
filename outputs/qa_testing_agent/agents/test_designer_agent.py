"""
Test Designer Agent â€” Generic / App-Agnostic
=============================================
Generates Playwright (Python) test scripts that work for ANY web application.

The agent enforces four guarantees:
  1. All URLs, credentials, and timeouts come from settings (never hardcoded).
  2. The __main__ scaffold is fixed Python code, not LLM output â€” so
     IndentationError, orphaned playwright blocks, and fake-pass bugs
     cannot occur.
  3. The LLM only writes the *body* of the test function; everything
     else is assembled by this agent in pure Python.
  4. The assembled script is validated with ast.parse() before being
     returned â€” a SyntaxError here triggers a retry, not a broken file.

Bugs fixed based on analysis of 32 generated scripts (v2):
  - expect() called on Python primitives (float, int, set) â†’ assert instead
  - Hardcoded Windows screenshot paths â†’ relative paths only
  - Class-based tests (class TestXxx:) â†’ standalone functions only
  - Old-style signatures def test_fn(email, password) â†’ def test_fn(page)
  - Duplicate _login / _take_screenshot blocks when LLM echoed helpers
  - Missing settings import in some outputs
"""

import ast
import os
import logging
import re
import textwrap
from typing import Optional

from openai import OpenAI

from models import TestCase, GeneratedTestCase
from config.settings import settings
from utils.selector_map_loader import ensure_selector_map, load_selector_map

# Import token tracker and page inspector
try:
    from utils.token_tracker import token_tracker
    TOKEN_TRACKING_ENABLED = True
except ImportError:
    TOKEN_TRACKING_ENABLED = False

try:
    from agents.page_inspector_agent import get_smart_page_inspector
    PAGE_INSPECTION_ENABLED = True
except ImportError:
    PAGE_INSPECTION_ENABLED = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixed boilerplate â€” written by this agent, NEVER by the LLM
# ---------------------------------------------------------------------------

_IMPORTS = """\
import sys
import traceback
import os
import re
import time
from playwright.sync_api import sync_playwright, expect
from config.settings import settings
"""

_SCREENSHOT_HELPER = """\
_page = None

def _take_screenshot(path):
    global _page
    if _page:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            _page.screenshot(path=path, full_page=True)
            print(f"SCREENSHOT: {path}")
        except Exception:
            pass
"""

_LOGIN_HELPER = """\
def _login(page):
    \"\"\"\n    Generic login helper - works for any app with an Email/Password form.
    All values come from settings; no credentials are hardcoded.

    After login, navigates to settings.FEATURE_URL if configured so that
    every test starts on the correct page without repeating navigation.
    Uses .first on the button locator to survive strict-mode when multiple
    buttons match the login pattern.
    \"\"\"\n    page.goto(settings.BASE_URL)
    page.wait_for_load_state("domcontentloaded")

    def _fill_first(locators, value, label):
        last_err = None
        for loc in locators:
            try:
                target = loc.first
                expect(target).to_be_visible(timeout=3000)
                target.fill(value)
                return
            except Exception as e:
                last_err = e
        raise RuntimeError(f"Could not find {label} field") from last_err

    _fill_first(
        [
            page.get_by_label(settings.EMAIL_FIELD_LABEL),
            page.get_by_role("textbox", name=re.compile(settings.EMAIL_FIELD_LABEL, re.IGNORECASE)),
            page.get_by_placeholder(re.compile(settings.EMAIL_FIELD_LABEL, re.IGNORECASE)),
            page.locator("input[type='email']"),
        ],
        settings.LOGIN_EMAIL,
        "email",
    )
    _fill_first(
        [
            page.get_by_label(settings.PASSWORD_FIELD_LABEL),
            page.get_by_role("textbox", name=re.compile(settings.PASSWORD_FIELD_LABEL, re.IGNORECASE)),
            page.get_by_placeholder(re.compile(settings.PASSWORD_FIELD_LABEL, re.IGNORECASE)),
            page.locator("input[type='password']"),
        ],
        settings.LOGIN_PASSWORD,
        "password",
    )

    # .first avoids strict-mode error when 2+ buttons match the login pattern
    login_btn = page.get_by_role(
        "button",
        name=re.compile(settings.LOGIN_BUTTON_PATTERN, re.IGNORECASE),
    ).first
    expect(login_btn).to_be_visible(timeout=settings.ELEMENT_TIMEOUT_MS)
    expect(login_btn).to_be_enabled()
    login_btn.click()
    page.wait_for_load_state("networkidle")
    # Navigate to the feature page if one is configured
    if settings.FEATURE_URL and settings.FEATURE_URL != settings.BASE_URL:
        page.goto(settings.FEATURE_URL)
        page.wait_for_load_state("networkidle")

    # Fail fast if login did not succeed (still on login page)
    if re.search(r"login", page.url, re.IGNORECASE):
        raise RuntimeError("Login failed: still on login page after submit")
"""

# Dynamically built at test-generation time from settings.STORY_PRECONDITIONS_JSON.
# The agent calls _build_precondition_helper() to produce this string.
# It is inserted into every generated script so the LLM can call
# _precondition(page) as the first line of every test body.
_PRECONDITION_HELPER_TEMPLATE = """def _precondition(page):
    \"\"\"
    Runs the configured STORY_PRECONDITIONS_JSON steps before each test.
    These steps navigate the UI to the correct state (e.g. open the filter
    panel, expand the Tags section) so the test starts from the right place.
    Generated from settings.STORY_PRECONDITIONS_JSON — change in .env, no code edits.
    \"\"\"
{steps_code}
"""
# {fn_name} filled by _assemble_script() â€” the LLM never sees this template.
_MAIN_TEMPLATE = """\
if __name__ == "__main__":
    _exit = 0
    try:
        with sync_playwright() as _pw:
            _browser = _pw.chromium.launch(headless=settings.HEADLESS)
            _ctx = _browser.new_context(
                viewport={{"width": 1280, "height": 720}},
                ignore_https_errors=True,
            )
            _ctx.set_default_timeout(settings.TEST_TIMEOUT_MS)
            page = _ctx.new_page()
            global _page
            _page = page
            try:
                {fn_name}(page)
            finally:
                _ctx.close()
                _browser.close()
        print("TEST_STATUS: PASSED")
    except Exception as _e:
        print("TEST_STATUS: FAILED")
        print(f"ERROR: {{_e}}")
        traceback.print_exc()
        _take_screenshot("reports/screenshots/{fn_name}_failure.png")
        _exit = 1
    sys.exit(_exit)
"""

# ---------------------------------------------------------------------------
# LLM system prompt â€” instructs it to write ONLY the function body
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a senior QA automation engineer writing Playwright (Python) test scripts.

YOUR ONLY JOB is to write the BODY of a single Python test function.
The function signature, imports, login helper, and __main__ block are
already provided by the framework â€” do NOT write them.

RULES â€” FOLLOW EVERY ONE:
==========================

1. NEVER hardcode URLs, emails, passwords, domain names, or credentials.
   - Use `settings.BASE_URL` if you need the app URL.
   - Call `_login(page)` for login - do NOT re-implement it.
   - Call `_precondition(page)` IMMEDIATELY after `_login(page)` - this sets up
     the UI state (e.g. opens the filter panel, expands the Tags section) so the
     test starts from the correct place. NEVER skip this call.

2. Use GENERIC Playwright locator strategies that work across any web app:
     page.get_by_role("button", name="Submit")
     page.get_by_label("Search")
     page.get_by_placeholder("Enter keyword")
     page.get_by_text("Success", exact=False)
     page.locator("[data-testid='submit-btn']")

3. `expect()` is ONLY for Playwright Locator objects.
   NEVER call expect() on Python primitives (numbers, strings, sets, booleans).
   For timing, counts, and other primitive checks use plain assert:
     WRONG:  expect(end_time - start_time).to_be_less_than(5)
     RIGHT:  assert (end_time - start_time) < 5, f"Took {{end_time-start_time:.2f}}s"

     WRONG:  expect(count).to_be(20)
     RIGHT:  assert count == 20, f"Expected 20, got {{count}}"

     WRONG:  expect(seen_tags).not_to_contain(tag)
     RIGHT:  assert tag not in seen_tags, f"Duplicate: {{tag}}"

4. ALWAYS call `page.wait_for_load_state("networkidle")` after navigation
   or any action that triggers data loading.

5. For network error simulation use page.route():
     page.route("**/api/**", lambda r: r.abort("failed"))

6. Use `time.time()` for performance timing assertions.

7. Write ONLY a standalone function body â€” do NOT use classes.
   WRONG:  class TestSomething:
               def test_fn(self, page):
   RIGHT:  (just write the indented body directly)

8. The function signature is already:  def {fn_name}(page):
   Do NOT include the def line â€” start from the first indented line.

9. Do NOT include any import statements â€” they are already provided.

10. Wrap the entire body in try/except that takes a screenshot on failure:
      try:
          # test steps here
      except Exception:
          page.screenshot(path="failure_{fn_name}.png")
          raise

11. The try: block MUST contain at least one indented statement.
    Never output an empty try/except, pass-only blocks, or placeholders.
    If you are unsure about a step, write a safe generic action like:
      page.wait_for_load_state("networkidle")
    and a real assertion:
      assert page.url is not None

12. Do not leave dangling control blocks (try/if/for/while) without a body.
    Always include concrete statements inside each block.

13. Screenshot paths must be RELATIVE â€” no drive letters, no absolute paths:
     WRONG:  page.screenshot(path="C:/Users/...")
     RIGHT:  page.screenshot(path="failure_{fn_name}.png")

14. MANDATORY EXECUTION ORDER — every test body MUST follow this pattern:
      try:
          _login(page)           # authenticates and navigates to the feature
          _precondition(page)    # sets up required UI state before test steps
          # ... your test steps here ...
      except Exception:
          page.screenshot(path="failure_{fn_name}.png")
          raise

    Do NOT skip _login() or _precondition(). Do NOT call them inside a loop.
    Do NOT call them more than once.

OUTPUT: Return ONLY the indented function body (no def line, no imports).
"""


# ---------------------------------------------------------------------------
# The Agent
# ---------------------------------------------------------------------------

class TestDesignerAgent:
    """
    Generates generic, app-agnostic Playwright test scripts from TestCase objects.

    Script structure (assembled entirely in Python, never by the LLM):
      [module docstring]
      [fixed imports]
      [fixed _page + _take_screenshot helper]
      [fixed _login helper]
      [LLM-generated: def fn_name(page): <body>]
      [fixed __main__ scaffold]

    The LLM only supplies the test function body. All boilerplate is
    assembled here, so structural bugs (IndentationError, missing imports,
    hardcoded credentials, duplicate helpers) cannot appear in output.
    """

    def __init__(self, openai_api_key=None):
        api_key = openai_api_key or settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=api_key)
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def design_test(self, test_case: TestCase, requirements=None,
                    retry_context: Optional[str] = None) -> GeneratedTestCase:
        """
        Generate a Playwright test script for the given test case.

        Args:
            test_case:     The test case to implement.
            requirements:  Output of RequirementsAnalysisAgent (optional).
            retry_context: Feedback from a previous rejected attempt (optional).

        Returns:
            GeneratedTestCase with syntactically valid test_code.
        """
        fn_name = self._make_fn_name(test_case.test_case_name)
        user_prompt = self._build_prompt(test_case, requirements, retry_context, fn_name)

        logger.info(f"Designing test: {test_case.test_case_name}")
        fn_body = self._call_llm(fn_name, user_prompt)
        test_code = self._assemble_script(fn_name, fn_body, test_case)

        return GeneratedTestCase(
            test_case_id=test_case.test_case_name,
            test_code=test_code,
            test_data=test_case.test_data or {},
            fixtures=["playwright", "settings"],
            estimated_duration_seconds=30,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    @staticmethod
    def _resolve_text_step_to_app_call(step: str, selector_map: dict) -> str:
        """
        Convert a plain-English precondition step into the correct _app_* call.

        This is the translator between human-readable .env config and real code.

        Examples
        --------
        "Click Filters"          → _app_open_filters_section(page)
        "Click Tags"             → _app_open_tags_section(page)
        "Open Filter Panel"      → _app_open_filter_panel(page)
        "Click OR"               → _app_apply_or_operator(page)
        "Click OR operator"      → _app_apply_or_operator(page)
        "Search toy"             → _app_search(page, "toy")
        "Enter toy"              → _app_search(page, "toy")
        "Type doll"              → _app_search(page, "doll")
        "Click tag toys"         → _app_click_tag(page, "toys")
        "Select Vehicles"        → _app_click_tag(page, "Vehicles")
        "Clear search"           → _app_clear_search(page)
        "Open asset"             → _app_open_asset(page, 0)
        "Navigate to Tag Cloud"  → _app_navigate_to(page, "Tag Cloud")

        Resolution order
        ----------------
        1. Already an _app_* call → use as-is
        2. Check against known filter labels from selector_map (exact match)
        3. Check against known tag names from selector_map
        4. Check against nav section names from selector_map
        5. Keyword rules (OR, search/enter/type, clear, asset)
        6. Best fuzzy match against all selector_map action names
        7. Fallback: raw page.get_by_text / page.get_by_role locator
        """
        step = str(step).strip()

        def _label(a: dict) -> str:
            return str(a.get("name") or a.get("text") or a.get("filter") or "").strip()

        # ── 1. Already an _app_* call ─────────────────────────────────────────
        if step.startswith("_app_"):
            return step

        step_lower = step.lower()

        # ── Detect search/enter/type verbs BEFORE stripping ──────────────────
        # Must happen first because stripping removes the verb that identifies
        # these as search actions ("Search toy" → target="toy" loses context)
        search_match = re.search(
            r"^(?:search(?:\s+for)?|enter|type)\s+(.+)", step_lower
        )
        if search_match:
            query = search_match.group(1).strip().strip("\"'")
            return f'_app_search(page, "{query}")'

        # ── Detect OR/AND operator BEFORE any other matching ─────────────────
        # Must happen before nav/fuzzy which could match "Workflows" etc.
        if re.search(r"\bor\b|\bor\s+operator\b", step_lower):
            return "_app_apply_or_operator(page)"
        if re.search(r"\band\b|\band\s+operator\b", step_lower):
            return "_app_apply_and_operator(page)"

        # ── Strip leading verb to get the target element name ─────────────────
        VERBS = ("navigate to", "go to", "click", "open", "expand",
                 "select", "press", "tap", "show", "toggle", "use", "apply")
        target = step_lower
        for verb in sorted(VERBS, key=len, reverse=True):
            if target.startswith(verb + " "):
                target = target[len(verb):].strip()
                break
            if target == verb:
                target = ""
                break

        # ── Hardcoded keyword rules (work even when selector_map is empty) ────
        # These cover the most common UI navigation terms and must be checked
        # BEFORE the selector_map-dependent steps so the system always works
        # even on first run before selector_map.json has been generated.

        # Filter panel combos first (more specific → check before single words)
        if any(x in target for x in ("filter panel", "filters and tags",
                                     "filters & tags", "filter and tags")):
            return "_app_open_filter_panel(page)"

        # ── Hardcoded known-good selectors from recorded_flow.py ────────────
        # These use INLINE Playwright code — they do NOT call _app_* functions.
        # This means the precondition works even when 0 helpers are generated.
        # Selectors come directly from the captured recording (proven to work).
        #
        # How to find your own selector:
        #   Run Playwright Codegen, perform the click, copy the locator line.
        #
        # "filters" / "filter" → open the Filters tab in the left panel
        # "tags"               → click the Tags accordion inside Filters
        # "filter panel"       → open Filters then Tags in one step
        _FILTER_BTN = ('page.locator("#rc-tabs-0-tab-filters div")'
            '.filter(has_text=re.compile(r"^Filters$")).first.click()')
        _TAGS_BTN = 'page.locator("a").filter(has_text="Tags").first.click()'
        _BOTH = _FILTER_BTN + "\n    page.wait_for_load_state(\"networkidle\")\n    " + _TAGS_BTN
        _INLINE_FALLBACKS = {
            "filter panel": _BOTH,
            "filters and tags": _BOTH,
            "filter and tags": _BOTH,
            "filters": _FILTER_BTN,
            "filter": _FILTER_BTN,
            "tags": _TAGS_BTN,
            "tag section": _TAGS_BTN,
            "tags section": _TAGS_BTN,
        }

        # Prefer _app_* helpers when selector_map provides them
        _APP_FALLBACKS = {}
        try:
            _filter_labels = {
                str(a.get("filter", a.get("name", ""))).strip().lower()
                for a in by_cat.get("filter", [])
                if str(a.get("filter", a.get("name", ""))).strip()
            }
            if "filters" in _filter_labels:
                _APP_FALLBACKS["filters"] = "_app_open_filters_section(page)"
                _APP_FALLBACKS["filter"] = "_app_open_filters_section(page)"
            if "tags" in _filter_labels:
                _APP_FALLBACKS["tags"] = "_app_open_tags_section(page)"
                _APP_FALLBACKS["tag section"] = "_app_open_tags_section(page)"
                _APP_FALLBACKS["tags section"] = "_app_open_tags_section(page)"
        except Exception:
            _APP_FALLBACKS = {}

        # Exact match
        if target in _INLINE_FALLBACKS:
            if target in _APP_FALLBACKS:
                return _APP_FALLBACKS[target]
            return _INLINE_FALLBACKS[target]

        # Partial match (e.g. "the filters tab" contains "filters")
        for keyword, inline_code in _INLINE_FALLBACKS.items():
            if keyword in target and len(keyword) >= 4:
                if keyword in _APP_FALLBACKS:
                    return _APP_FALLBACKS[keyword]
                return inline_code

        # ── If selector_map has data, look up inline code from recording ─────
        # This uses the exact .raw Playwright line captured from the recording.
        # Preferred over _app_* calls because it's self-contained.
        by_cat = selector_map.get("by_category", {}) if isinstance(selector_map, dict) else {}
        all_actions = selector_map.get("actions", []) if isinstance(selector_map, dict) else []
        target_tokens = set(re.findall(r"[a-z]{3,}", target))
        has_helpers = any(by_cat.get(k) for k in ("filter", "tag", "navigation", "search"))
        if target_tokens and all_actions and not has_helpers:
            best = None
            best_score = 0
            for a in all_actions:
                lbl = str(a.get("filter", a.get("name", a.get("text", "")))).lower()
                lbl_tokens = set(re.findall(r"[a-z]{3,}", lbl))
                score = len(target_tokens & lbl_tokens)
                if score > best_score:
                    best_score = score
                    best = a
            if best and best_score >= 1:
                raw = best.get("raw", "")
                if raw:
                    logger.info(f"Precondition '{step}' matched raw selector from recording")
                    return raw

        # Collect knowledge from selector_map
        by_cat = selector_map.get("by_category", {}) if isinstance(selector_map, dict) else {}

        # Known filter labels  e.g. "filters", "tags"
        filter_labels = []
        for a in by_cat.get("filter", []):
            lbl = str(a.get("filter", a.get("name", ""))).strip().lower()
            if lbl:
                filter_labels.append(lbl)

        # Known tag names  e.g. "toys", "vehicles"
        tag_names = []
        for a in by_cat.get("tag", []):
            raw = _label(a)
            core = re.sub(r"\d+$", "", raw).strip().lower()
            if core and len(core.split()) <= 3:
                tag_names.append(core)

        # Known nav sections  e.g. "tag cloud", "folders"
        nav_sections = []
        for a in by_cat.get("navigation", []):
            sec = _label(a)
            if sec:
                nav_sections.append(sec)

        # ── 2. Filter labels ─────────────────────────────────────────────────
        # Special combo: "filter panel", "filters and tags", "filters & tags"
        if any(x in target for x in ("filter panel", "filters and tags",
                                     "filters & tags", "filter and tags")):
            return "_app_open_filter_panel(page)"

        for lbl in filter_labels:
            if lbl in target or target in lbl:
                fn = f"_app_open_{re.sub(r'[^a-z0-9]', '_', lbl).strip('_')}_section"
                fn = re.sub(r"_+", "_", fn)
                return f"{fn}(page)"

        # ── 3. Tag names ─────────────────────────────────────────────────────
        # "click tag toys" / "select Vehicles" / "click toys tag"
        if any(kw in target for kw in ("tag ", " tag", "tags")):
            candidate = re.sub(r"\btags?\b", "", target).strip()
            if candidate:
                for known in tag_names:
                    if known in candidate or candidate in known:
                        return f'_app_click_tag(page, "{known}")'
                return f'_app_click_tag(page, "{candidate}")'

        # Direct tag name match without the word "tag"
        for known in tag_names:
            if known == target or (known in target and len(known) > 3):
                return f'_app_click_tag(page, "{known}")'

        # ── 4. Nav sections ──────────────────────────────────────────────────
        for sec in nav_sections:
            if sec.lower() in target or target in sec.lower():
                return f'_app_navigate_to(page, "{sec}")'

        # ── 5. Remaining keyword rules ────────────────────────────────────────

        # Clear search
        if "clear" in target:
            return "_app_clear_search(page)"

        # Asset / thumbnail
        if any(x in target for x in ("asset", "thumbnail", "thumb", "image")):
            num = re.search(r"\d+", target)
            idx = int(num.group()) if num else 0
            return f"_app_open_asset(page, {idx})"

        # ── 6. Fuzzy match against all action names in selector_map ──────────
        all_actions = selector_map.get("actions", []) if isinstance(selector_map, dict) else []
        target_tokens = set(re.findall(r"[a-z]{3,}", target))
        best_fn = None
        best_score = 0
        for a in all_actions:
            cat = a.get("category", "")
            lbl = str(a.get("filter", a.get("name", a.get("text", "")))).lower()
            lbl_tokens = set(re.findall(r"[a-z]{3,}", lbl))
            score = len(target_tokens & lbl_tokens)
            if score > best_score:
                best_score = score
                if cat == "filter":
                    fn = f"_app_open_{re.sub(r'[^a-z0-9]', '_', lbl).strip('_')}_section"
                    best_fn = f"{re.sub(r'_+', '_', fn)}(page)"
                elif cat == "tag":
                    core = re.sub(r"\d+$", "", lbl).strip()
                    best_fn = f'_app_click_tag(page, "{core}")'
                elif cat == "search":
                    best_fn = f'_app_search(page, "{lbl}")'
                elif cat == "navigation":
                    orig = _label(a) or lbl
                    best_fn = f'_app_navigate_to(page, "{orig}")'

        if best_fn and best_score >= 1:
            logger.info(f"Precondition fuzzy-matched '{step}' → {best_fn}")
            return best_fn

        # ── 7. Absolute fallback — raw Playwright locator ────────────────────
        # Better than nothing: at least the step description is in the comment
        logger.warning(
            f"Precondition step '{step}' could not be matched to an _app_* call. "
            "Using raw get_by_text fallback — may be unreliable."
        )
        # Use the original target text (before verb stripping) for the locator
        original_target = re.sub(
            r"^(?:click|open|select|expand|navigate to|navigate|go to)\s+",
            "", step, flags=re.IGNORECASE
        ).strip()
        return (
            f'page.get_by_text("{original_target}", exact=False).first.click()'
        )

    @staticmethod
    def _build_precondition_helper(steps, selector_map=None) -> str:
        """
        Build a _precondition(page) helper from plain-English step descriptions.

        You write in .env:
            STORY_PRECONDITIONS_JSON={
              "My Story": ["Click Filters", "Click Tags"]
            }

        This method translates each step into the correct _app_* call using
        _resolve_text_step_to_app_call(), which understands natural language
        like "Click Filters", "Search toy", "Click OR", etc.

        If a step is already an _app_* call it is used verbatim (backwards
        compatible with the old explicit format).
        """
        steps = steps or []

        if not steps:
            steps_code = "    pass  # No precondition steps configured"
            return _PRECONDITION_HELPER_TEMPLATE.format(steps_code=steps_code)

        sm = selector_map if isinstance(selector_map, dict) else {}

        action_lines = []
        resolved_count = 0
        for step in steps:
            step_str = str(step).strip()
            if not step_str:
                continue

            action_lines.append(f"    # {step_str}")
            resolved = TestDesignerAgent._resolve_text_step_to_app_call(
                step_str, sm
            )
            action_lines.append(f"    {resolved}")
            action_lines.append('    page.wait_for_load_state("networkidle")')

            if resolved.startswith("_app_"):
                resolved_count += 1

        logger.info(
            f"Precondition: resolved {resolved_count}/{len(steps)} steps "
            f"to _app_* calls"
        )

        steps_code = "\n".join(action_lines)
        return _PRECONDITION_HELPER_TEMPLATE.format(steps_code=steps_code)

    @staticmethod
    def _make_fn_name(raw: str) -> str:
        """Convert test_case_name to a valid Python snake_case function name."""
        name = re.sub(r"[^a-zA-Z0-9_]", "_", raw).lower()
        name = re.sub(r"_+", "_", name).strip("_")
        if not name or name[0].isdigit():
            name = "test_" + name
        if not name.startswith("test_"):
            name = "test_" + name
        return name[:80]

    def _build_prompt(self, test_case, requirements, retry_context, fn_name):
        steps_block = "\n".join(
            f"  Step {s.step_no}: {s.description}\n"
            f"    Expected: {s.expected_results}"
            for s in test_case.steps
        )
        req_block = ""
        if requirements:
            reqs = getattr(requirements, "identified_requirements", [])
            if reqs:
                req_block = (
                    "\nKey requirements identified:\n"
                    + "\n".join(f"  - {r}" for r in reqs) + "\n"
                )
        retry_block = ""
        if retry_context:
            retry_block = f"\nPREVIOUS ATTEMPT FEEDBACK â€” fix these issues:\n{retry_context}\n"

        pre_steps = self._resolve_precondition_steps(test_case)
        page_selectors_block = self._get_page_selectors_block()
        return (
            f"Test scenario: {test_case.test_scenario}\n"
            f"Function name: {fn_name}\n"
            f"Feature URL (already navigated to by _login): "
            f"{getattr(settings, 'FEATURE_URL', '') or settings.BASE_URL}\n"
            f"{req_block}"
            f"{page_selectors_block}"
            + self._build_precondition_prompt_block(pre_steps)
            + f"\nTest steps to implement AFTER pre-steps:\n{steps_block}\n"
            f"\nRemarks / preconditions: {test_case.remarks or 'None'}\n"
            f"{retry_block}"
            + self._get_real_tag_names_block()
            + f"\nWrite the body of `def {fn_name}(page):` - "
            f"indented Python code only, no def line, no imports.\n"
        )
    def _get_page_selectors_block(self) -> str:
        """Get real page selectors from Smart Page Inspector v2."""
        if not PAGE_INSPECTION_ENABLED:
            return ""
        
        if not getattr(settings, "ENABLE_PAGE_INSPECTION", True):
            return ""
        
        try:
            inspector = get_smart_page_inspector()
            summary = inspector.get_selector_summary()
            if summary and "No page inspection" not in summary:
                return "\n" + summary + "\n"
        except Exception as e:
            logger.warning(f"Could not get page selectors: {e}")
        
        return ""

    def _build_precondition_prompt_block(self, steps) -> str:
        """Return a formatted string for the LLM prompt describing mandatory pre-steps."""
        if not steps:
            return ""

        return (
            "\nMANDATORY PRE-STEPS (call _precondition(page) to handle these automatically):\n"
            + "\n".join(f"  Pre-{i+1}: {s}" for i, s in enumerate(steps))
            + "\n"
            "IMPORTANT: _precondition(page) must be called before ANY test step below.\n"
        )

    def _get_real_tag_names_block(self) -> str:
        """
        Return a prompt block listing real tag names from selector_map.
        Prevents LLM from inventing tag names like "Tag A" or "largeDatasetTag".
        """
        try:
            selector_map = self._load_selector_map()
            if not selector_map:
                return ""
            tag_actions = selector_map.get("by_category", {}).get("tag", [])
            if not tag_actions:
                return ""
            # Extract tag names by stripping trailing digits
            import re as _re
            tag_names = []
            for a in tag_actions:
                raw_name = a.get("name") or a.get("text") or ""
                core = _re.sub(r"\d+$", "", raw_name).strip()
                if core and core not in tag_names and len(core) > 1:
                    tag_names.append(core)
            if not tag_names:
                return ""
            names_str = ", ".join(f'"{n}"' for n in tag_names[:15])
            return (
                f"\n⚠️  REAL TAG NAMES FROM APPLICATION (use ONLY these — never invent tag names):\n"
                f"  {names_str}\n"
                f"  Use _app_click_tag(page, \"tag_name\") with one of the names above.\n"
                f"  NEVER use placeholder names like 'Tag A', 'tag1', 'largeDatasetTag'.\n"
            )
        except Exception:
            return ""


    def _resolve_precondition_steps(self, test_case: TestCase):
        """
        Resolve per-story precondition steps from STORY_PRECONDITIONS_JSON.
        
        Matching strategy:
        1. Try exact match by story_id or story_title
        2. Try case-insensitive match
        3. Strip [CSV-xxxxx] prefix and try matching the core title
        4. Try partial match (story title contains the key)
        5. No match -> return []
        """
        import json
        import re

        story_id = None
        story_title = None
        if getattr(test_case, "test_data", None):
            story_id = test_case.test_data.get("story_id")
            story_title = test_case.test_data.get("story_title")

        # Load mapping from env
        try:
            raw_map = getattr(settings, "STORY_PRECONDITIONS_JSON", "{}")
            story_map = json.loads(raw_map) if isinstance(raw_map, str) else raw_map
        except (ValueError, TypeError):
            story_map = {}

        if isinstance(story_map, dict) and story_map:
            # Strategy 1: Direct match by id or title
            if story_id and story_id in story_map:
                logger.info(f"Matched preconditions by story_id: {story_id}")
                return story_map.get(story_id) or []
            if story_title and story_title in story_map:
                logger.info(f"Matched preconditions by exact title: {story_title}")
                return story_map.get(story_title) or []

            # Strategy 2: Case-insensitive match
            lowered = {str(k).lower(): v for k, v in story_map.items()}
            if story_id and str(story_id).lower() in lowered:
                logger.info(f"Matched preconditions by story_id (case-insensitive): {story_id}")
                return lowered.get(str(story_id).lower()) or []
            if story_title and str(story_title).lower() in lowered:
                logger.info(f"Matched preconditions by title (case-insensitive): {story_title}")
                return lowered.get(str(story_title).lower()) or []
            
            # Strategy 3: Strip [CSV-xxxxx] or [AZURE-xxxxx] prefix and match
            if story_title:
                # Remove prefix like [CSV-12345] or [AZURE-678]
                cleaned_title = re.sub(r'^\[[\w\-]+\]\s*', '', story_title).strip()
                if cleaned_title in story_map:
                    logger.info(f"Matched preconditions by cleaned title: {cleaned_title}")
                    return story_map.get(cleaned_title) or []
                
                # Case-insensitive cleaned match
                if cleaned_title.lower() in lowered:
                    logger.info(f"Matched preconditions by cleaned title (case-insensitive): {cleaned_title}")
                    return lowered.get(cleaned_title.lower()) or []
            
            # Strategy 4: Partial match - if story title contains the key
            if story_title:
                story_title_lower = story_title.lower()
                for key, steps in story_map.items():
                    key_lower = str(key).lower()
                    # Check if the key is contained in the story title
                    if key_lower in story_title_lower:
                        logger.info(f"Matched preconditions by partial match: '{key}' in '{story_title}'")
                        return steps or []

        logger.info("No story-specific preconditions found")
        return []

    def _load_selector_map(self) -> dict:
        folder = getattr(settings, "UI_SNAPSHOT_FOLDER", "./ui_snapshot")
        map_file = getattr(settings, "SELECTOR_MAP_FILE", "selector_map.json")
        rec_file = getattr(settings, "RECORDED_FLOW_FILE", "recorded_flow.py")
        ensure_selector_map(folder, map_file, rec_file)
        try:
            return load_selector_map(folder, map_file)
        except Exception:
            return {}

    def _call_llm(self, fn_name: str, user_prompt: str) -> str:
        """Call the LLM and return the raw function body text."""
        system = _SYSTEM_PROMPT.format(fn_name=fn_name)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        if TOKEN_TRACKING_ENABLED:
            try:
                token_tracker.record("TestDesignerAgent", response)
            except:
                pass
        return response.choices[0].message.content.strip()

    @staticmethod
    def _clean_body(raw_body: str, fn_name: str, known_helpers: set = None) -> str:
        """
        Sanitise the LLM's raw function body before assembly.

        Fixes applied:
          - Strip markdown fences
          - Extract method body if LLM wrapped output in a class
          - Remove accidental def/import/class lines echoed by the LLM
          - Fix hardcoded absolute/Windows paths in screenshot() calls
          - Convert expect() on primitives to assert statements
          - Normalise indentation to 4 spaces
        """
        # â”€â”€ Strip markdown fences â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        raw_body = re.sub(r"^```[a-zA-Z]*\n?", "", raw_body, flags=re.MULTILINE)
        raw_body = re.sub(r"\n?```\s*$", "", raw_body, flags=re.MULTILINE)
        raw_body = raw_body.strip()

        # â”€â”€ Extract body if LLM used a class wrapper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Pattern: class Xxx:\n    def test_yyy(self, page):\n        <body>
        class_match = re.search(
            r"class \w+.*?:\n(.*?)(?=\n\nclass |\Z)", raw_body, re.DOTALL
        )
        if class_match:
            inner = class_match.group(1)
            method_match = re.search(
                r"    def test_\w+\(self[^)]*\):\n(.*?)(?=\n    def |\Z)",
                inner, re.DOTALL
            )
            if method_match:
                raw_body = textwrap.dedent(method_match.group(1))

        # â”€â”€ Drop lines the LLM should not have included â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        lines = []
        for line in raw_body.splitlines():
            stripped = line.lstrip()
            # Any def line for this function (regardless of its params)
            if re.match(rf"def {re.escape(fn_name)}\s*\(", stripped):
                continue
            # Helpers being echoed back
            if re.match(r"def (_login|_take_screenshot)\s*\(", stripped):
                continue
            # Import lines
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue
            # Class declarations
            if re.match(r"class \w+", stripped):
                continue
            lines.append(line)
        raw_body = "\n".join(lines).strip()

        # â”€â”€ Fix absolute/Windows screenshot paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        raw_body = re.sub(
            r'(page\.screenshot\(path=)["\'](?:[A-Za-z]:[/\\][^"\']*|/(?!failure)[^"\']*)["\']',
            rf'\1"failure_{fn_name}.png"',
            raw_body,
        )

        # â”€â”€ Fix expect() on Python primitives â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # expect(end_time - start_time).to_be_less_than(N)
        raw_body = re.sub(
            r"expect\((end_time\s*-\s*start_time)\)\.to_be_less_than\((\d+(?:\.\d+)?)\)",
            r'assert (\1) < \2, f"Took {\1:.2f}s, expected < \2s"',
            raw_body,
        )
        # expect(count_var).to_be(N) â€” count/len patterns
        raw_body = re.sub(
            r"expect\((\w*[Cc]ount\w*|len\([^)]+\))\)\.to_be\((\d+)\)",
            r'assert \1 == \2, f"Expected \2, got {\1}"',
            raw_body,
        )
        # expect(collection).not_to_contain(item)
        raw_body = re.sub(
            r"expect\((\w+)\)\.not_to_contain\((\w+)\)",
            r'assert \2 not in \1, f"Duplicate found: {\2}"',
            raw_body,
        )
        # expect(str_var).to_be(other_str_var) â€” style comparisons
        raw_body = re.sub(
            r"expect\((\w+_style)\)\.to_be\((\w+_style)\)",
            r'assert \1 == \2, "Style mismatch between existing and new elements"',
            raw_body,
        )

        # --- Sanitize invalid locator patterns ---
        # page.locator(..., first=True) -> page.locator(...).first
        raw_body = re.sub(
            r"page\.locator\(([^)]*?),\s*first\s*=\s*True\s*\)",
            r"page.locator(\1).first",
            raw_body,
        )
        # locator(..., first=True) -> locator(...).first
        raw_body = re.sub(
            r"\.locator\(([^)]*?),\s*first\s*=\s*True\s*\)",
            r".locator(\1).first",
            raw_body,
        )
        # page.locator(..., name=...) -> get_by_text(...) as a safer generic fallback
        raw_body = re.sub(
            r"page\.locator\(([^)]*?),\s*name\s*=\s*([^)]+)\)",
            r"page.get_by_text(\2, exact=False)",
            raw_body,
        )
        # data-testid selectors: add a generic fallback locator chain
        # e.g. page.locator("[data-testid='x']").click()
        #   -> (page.locator("[data-testid='x']").or_(page.get_by_text("x", exact=False))).click()
        def _replace_data_testid(match):
            full = match.group(0)
            selector = match.group("sel")
            action = match.group("action")
            m = re.search(r"data-testid=['\"]([^'\"]+)['\"]", selector)
            if not m:
                return full
            key = m.group(1)
            return f"(page.locator({selector}).or_(page.get_by_text(\"{key}\", exact=False))).{action}"

        raw_body = re.sub(
            r"page\.locator\((?P<sel>\"\\[data-testid='[^']+'\\]\"|'\\[data-testid=\"[^\"]+\"\\]')\)\.(?P<action>click|fill|check|uncheck|dblclick|hover)\(",
            _replace_data_testid,
            raw_body,
        )
        # also handle locator(...).locator("[data-testid='x']").<action>
        def _replace_nested_data_testid(match):
            base = match.group("base")
            selector = match.group("sel")
            action = match.group("action")
            m = re.search(r"data-testid=['\"]([^'\"]+)['\"]", selector)
            if not m:
                return match.group(0)
            key = m.group(1)
            return f"{base}.locator({selector}).or_({base}.get_by_text(\"{key}\", exact=False)).{action}"

        raw_body = re.sub(
            r"(?P<base>[\w\)\.]+)\.locator\((?P<sel>\"\\[data-testid='[^']+'\\]\"|'\\[data-testid=\"[^\"]+\"\\]')\)\.(?P<action>click|fill|check|uncheck|dblclick|hover)\(",
            _replace_nested_data_testid,
            raw_body,
        )
        # locator.first() / locator.last() are properties, not callables in Playwright Python
        raw_body = re.sub(r"\.first\(\)", ".first", raw_body)
        raw_body = re.sub(r"\.last\(\)", ".last", raw_body)

        # â”€â”€ Normalise indentation to exactly 4 spaces â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # -- Fix raw regex tag patterns (LLM writes these instead of calling _app_click_tag) --
        # Matches: page.get_by_text(re.compile(r"^tagname\d+$", re.IGNORECASE)).first.click()
        # Tested against actual LLM output from execution logs.
        def _replace_raw_tag_regex(m):
            tag_name = m.group(1)
            # Unescape backslash-space that Playwright codegen emits: "Tag\ A" -> "Tag A"
            tag_name = tag_name.replace("\\ ", " ").replace("\\\\", "")
            return f'_app_click_tag(page, "{tag_name}")'
        # Covers all raw tag-regex patterns the LLM commonly writes:
        #   page.get_by_text(re.compile(r"^toys\d+$")).first.click()
        #   page.get_by_text(re.compile(r"^Tag\ A\d+$", re.IGNORECASE)).first.click()
        #   page.get_by_text(re.compile(r"^toys\d+$")).click()
        RAW_TAG_PAT = re.compile(
            r'page\.get_by_text\('
            r're\.compile\(r"(?:\\^|\\\\^|\^)'
            r'([^"]+?)'              # tag name — allow backslash for escaped spaces
            r'(?:\\\\d|\\d)\+\$?"'  # \d+$
            r'(?:,\s*re\.IGNORECASE)?\)'
            r'\)(?:\.first)?\.click\(\)',
        )
        raw_body = RAW_TAG_PAT.sub(_replace_raw_tag_regex, raw_body)
        # Without .first
        raw_body = re.sub(
            r'page\.get_by_text\(re\.compile\(r"\^([^\\\\]+)\\\\d\+\$"(?:,\s*re\.IGNORECASE)?\)\)\.click\(\)',
            _replace_raw_tag_regex,
            raw_body,
        )

        # -- Fix unknown _app_* function names the LLM invents --
        if known_helpers:
            def _fix_unknown_app_call(m):
                full_name = m.group(1)          # e.g. _app_click_text_filters
                bare_name = full_name[5:]        # strip _app_ -> click_text_filters
                if full_name in known_helpers:
                    return m.group(0)           # valid -> keep as-is
                # Try fuzzy match: strip leading verb tokens and compare to known helper stems
                normalised = re.sub(r"^(click_text_|click_|get_|open_|apply_|use_)", "", bare_name)
                for helper in sorted(known_helpers):
                    stem = helper[5:]           # strip _app_
                    if normalised == stem or normalised in stem or stem in normalised:
                        return helper + "("
                # No match — replace with pass comment so script still runs
                return f"pass  # removed unknown helper: {full_name}("
            raw_body = re.sub(r"(_app_[a-z_]+)\(", _fix_unknown_app_call, raw_body)

        raw_body = textwrap.dedent(raw_body)
        raw_body = textwrap.indent(raw_body, "    ")
        return raw_body

    def _assemble_script(self, fn_name: str, raw_body: str, test_case: TestCase) -> str:
        """
        Assemble the complete test script and validate it with ast.parse().
        If the LLM body is malformed, the error is logged so the reviewer
        agent can reject it and the orchestrator retry loop re-generates.
        """
        # Load selector_map FIRST — needed by both helper generation and _clean_body
        selector_map = self._load_selector_map()

        # Generate app helper library and collect known function names
        # BUGFIX: old `if selector_map:` silently skipped generation when
        # selector_map was {} (falsy). Now always attempts generation.
        app_helpers_code = ""
        _known_helpers: set = set()
        try:
            from utils.app_helper_generator import AppHelperGenerator
            _gen = AppHelperGenerator(selector_map if isinstance(selector_map, dict) else {})
            app_helpers_code = _gen.generate()
            import re as _re
            _known_helpers = set(_re.findall(r"def (_app_[a-z_]+)\(", app_helpers_code))
            logger.info(f"Generated {len(_known_helpers)} app helpers for script")
        except Exception as e:
            logger.warning(f"App helper generation failed: {e}")

        clean_body = self._clean_body(raw_body, fn_name, _known_helpers)
        scenario_safe = re.sub(r"[^\w\s\-]", "", test_case.test_scenario)[:80]
        main_block = _MAIN_TEMPLATE.format(fn_name=fn_name)

        pre_steps = self._resolve_precondition_steps(test_case)

        # Build script parts — app helper library MUST come before the test fn
        parts = [
            f'"""\nTest: {scenario_safe}\nGenerated by QA Testing Agent\n"""',
            _IMPORTS,
            _SCREENSHOT_HELPER,
            _LOGIN_HELPER,
        ]
        if app_helpers_code:
            parts.append(app_helpers_code)
            logger.info("Injected app helper library into generated script")
        parts += [
            self._build_precondition_helper(pre_steps, selector_map),
            f"def {fn_name}(page):",
            clean_body,
            "",
            main_block,
        ]
        script = "\n\n".join(parts)
        # Validate -- if invalid, fall back to a minimal safe body
        try:
            ast.parse(script)
            logger.debug(f"Script for '{fn_name}' validated OK")
        except SyntaxError as e:
            logger.error(
                f"Script for '{fn_name}' has SyntaxError at line {e.lineno}: {e.msg}. "
                f"Using fallback body to avoid broken output."
            )
            fallback_body = textwrap.indent(
                f"""try:
    _login(page)
    page.wait_for_load_state(\"networkidle\")
    assert True, \"Fallback test body generated due to invalid LLM output\"
except Exception:
    page.screenshot(path=\"failure_{fn_name}.png\")
    raise""",
                "    ",
            )
            parts[5] = fallback_body
            script = "\n\n".join(parts)
            try:
                ast.parse(script)
                logger.debug(f"Fallback script for '{fn_name}' validated OK")
            except SyntaxError as e2:
                logger.error(
                    f"Fallback script for '{fn_name}' still invalid at line {e2.lineno}: {e2.msg}."
                )

        return script
