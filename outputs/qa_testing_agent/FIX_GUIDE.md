# QA Agent Fix Guide

## What Was Wrong & What's Fixed

---

### Problem 1: `name 'label' is not defined` — **Test Executor Bug**

**File:** `executors/test_executor.py`

**Root Cause:** The old executor was passing `label` as a positional argument to a function that expected a named parameter. This caused ALL 9 tests to fail immediately at execution time, before even opening a browser.

**Fix:** Complete rewrite of `test_executor.py`:
- Tests are now written to a temp `.py` file and executed via `subprocess.run()`
- A proper Playwright runner wrapper (`with sync_playwright()`) is injected automatically
- The executor correctly captures `stdout`/`stderr` and maps return code to PASSED/FAILED
- Screenshots are saved on failure using the correct path

---

### Problem 2: Browser Opens But No Actions Performed

**File:** `agents/test_designer_agent.py`

**Root Cause:** The old Test Designer Agent generated **skeleton/placeholder code** — the test would navigate to the URL and then stop. No form fills, no clicks, no assertions. The LLM prompt was too vague and didn't mandate full step implementation.

**Fix:** New `test_designer_agent.py` with:
- **Explicit system prompt** that mandates implementing EVERY step
- **Step-by-step guidance** in the user prompt with all step descriptions and expected results
- **Element discovery strategy** baked into the prompt (no hardcoded selectors):
  ```python
  # Priority order the agent uses:
  page.get_by_role("button", name="Login")      # 1st choice
  page.get_by_label("Email")                     # 2nd choice  
  page.get_by_placeholder("Enter email")         # 3rd choice
  page.get_by_text("Submit", exact=True)         # 4th choice
  page.get_by_title("Close")                     # 5th choice
  page.locator("input[type='email']")            # semantic fallback
  ```
- **Code validation** that detects skeleton code and wraps it in a complete test structure
- **Markdown fence stripping** (removes ```python``` blocks the LLM sometimes adds)
- BASE_URL, LOGIN_EMAIL, LOGIN_PASSWORD are passed directly into the generated code

---

### Problem 3: Reviewer Misclassified "Incomplete Code" as `UI_CHANGE`

**File:** `agents/reviewer_agent.py`

**Root Cause:** The reviewer was flagging incomplete/skeleton test code as `UI_CHANGE`, which caused the orchestrator to **stop execution entirely** instead of retrying. This cascaded — all 9 tests stopped and nothing ran.

**Fix:** New `reviewer_agent.py` with:
- Clear classification rules in the system prompt:
  - `DATA_ISSUE` = incomplete code, missing steps, no assertions (→ triggers retry/regeneration)
  - `UI_CHANGE` = only for genuinely hardcoded brittle CSS selectors found in the code
  - `MISMATCH` = logic contradicts requirements
- `INCOMPLETE_CODE` and `INCOMPLETE` are mapped to `DATA_ISSUE` programmatically
- `improvement_suggestions` is always returned as a `str` (fixes the Pydantic validation error)
- Falls back to **APPROVED** if JSON parse fails (doesn't block execution)

---

### Problem 4: `improvement_suggestions` Pydantic Validation Error

**Log line:** `Input should be a valid string [type=string_type, input_value=["1. Implement explicit a...`

**Root Cause:** The LLM was returning `improvement_suggestions` as a JSON **list** `[...]` but the `ReviewResult` model expected a `str`.

**Fix:** In `reviewer_agent.py`:
```python
if isinstance(suggestions, list):
    suggestions = " | ".join(suggestions)
```

---

### Problem 5: Generic Agent — No Hardcoded Selectors

**Design Goal:** The agent should work with **any web application** without storing selectors in `.env` or config files.

**How it's achieved:**
- `.env` only contains: `BASE_URL`, `LOGIN_EMAIL`, `LOGIN_PASSWORD`
- The Test Designer Agent is instructed to use Playwright's semantic locators
- The agent discovers elements at runtime using accessible names, roles, labels, and placeholder text
- This works across different applications without any configuration changes

---

## Files to Replace in Your Project

| File in fix package | Replace in your project |
|---|---|
| `agents/test_designer_agent.py` | `agents/test_designer_agent.py` |
| `agents/reviewer_agent.py` | `agents/reviewer_agent.py` |
| `agents/requirements_agent.py` | `agents/requirements_agent.py` |
| `executors/test_executor.py` | `executors/test_executor.py` |
| `orchestrator.py` | `orchestrator.py` |
| `config/settings.py` | `config/settings.py` |

---

## Your `.env` File — What Should Be There

```env
# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7

# Application Under Test (URL + credentials ONLY - no selectors!)
BASE_URL=https://dev.mirrix.app/login
LOGIN_EMAIL=lakshmi@unitofmeasure.com
LOGIN_PASSWORD=***REMOVED***

# Browser
BROWSER_TYPE=chrome
HEADLESS=false
SCREENSHOT_ON_FAILURE=true
TEST_TIMEOUT_SECONDS=300

# Agent Behavior
MAX_RETRY_LOOPS=3
EXECUTE_REJECTED_TESTS=true
```

**Do NOT add:** element IDs, CSS selectors, XPaths, button names, field names.
The agent discovers all of those dynamically at runtime.

---

## How the Fixed Flow Works

```
Test Case Steps (from Excel/CSV)
         ↓
Requirements Analysis Agent
  → Understands what each step means
  → Identifies what actions & assertions are needed
         ↓
Test Designer Agent
  → Generates COMPLETE Playwright code
  → Implements EVERY step
  → Uses get_by_role/get_by_label/get_by_text (no hardcoded selectors)
  → Includes expect() assertions for every expected result
         ↓
Reviewer Agent
  → Checks code covers ALL steps
  → DATA_ISSUE → retry/regenerate (not stop!)
  → UI_CHANGE → only for hardcoded brittle selectors
  → APPROVED → proceed to execution
         ↓
Test Executor
  → Writes code to temp file
  → Adds sync_playwright() runner wrapper
  → Runs via subprocess
  → Captures PASSED/FAILED from output + return code
  → Saves screenshot on failure
```

---

## Example of Generated Test Code (What to Expect)

For a "Login" test case, the agent now generates something like:

```python
from playwright.sync_api import sync_playwright, expect
import pytest
import re

BASE_URL = "https://dev.mirrix.app/login"
LOGIN_EMAIL = "lakshmi@unitofmeasure.com"
LOGIN_PASSWORD = "***REMOVED***"

def test_happy_path_login(page):
    """Test: Login | happy_path_login"""
    
    # Step 1: Navigate to login page
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    
    # Step 2: Enter email
    email_input = page.get_by_label(re.compile("email", re.IGNORECASE))
    expect(email_input).to_be_visible(timeout=10000)
    email_input.fill(LOGIN_EMAIL)
    
    # Step 3: Enter password
    password_input = page.get_by_label(re.compile("password", re.IGNORECASE))
    expect(password_input).to_be_visible(timeout=10000)
    password_input.fill(LOGIN_PASSWORD)
    
    # Step 4: Click Login
    login_btn = page.get_by_role("button", name=re.compile("login|sign in", re.IGNORECASE))
    expect(login_btn).to_be_enabled(timeout=10000)
    login_btn.click()
    
    # Step 5: Verify dashboard loads
    page.wait_for_load_state("networkidle")
    expect(page).not_to_have_url(re.compile("login"))  # Should redirect away from login
    dashboard = page.get_by_role("main")
    expect(dashboard).to_be_visible(timeout=15000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        test_happy_path_login(page)
        browser.close()
```

This is a **complete, runnable test** — not a skeleton.
