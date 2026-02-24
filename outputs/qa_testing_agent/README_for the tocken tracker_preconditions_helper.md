# QA Testing Agent - Updated Files Package
**Date:** February 18, 2026  
**Version:** 3.0 - Bug fixes + Token tracking + Precondition system

---

## 📦 What's in this package

This package contains 7 updated files with three major improvements:

1. **Bug Fixes** - Tests now execute properly with visible browser option
2. **Token Usage Tracking** - See exactly how many tokens and $ each agent uses
3. **Precondition System** - Handle multi-step UI setup before test steps (completely generic)

---

## 🚀 Quick Start - Installation

### Step 1: Backup your current files (optional but recommended)
```bash
# From your project root
mkdir backup_$(date +%Y%m%d)
cp agents/requirements_agent.py backup_*/
cp agents/reviewer_agent.py backup_*/
cp agents/test_designer_agent.py backup_*/
cp executors/test_executor.py backup_*/
cp config/settings.py backup_*/
cp main.py backup_*/
```

### Step 2: Copy all files to your project
```bash
# Copy the updated files (preserving directory structure)
cp -r updated_files/agents/* your_project/agents/
cp -r updated_files/utils/* your_project/utils/
cp -r updated_files/config/* your_project/config/
cp -r updated_files/executors/* your_project/executors/
cp updated_files/main.py your_project/
```

### Step 3: Configure your .env file
Add these new settings to your `.env` or `_env` file:

```bash
# ============================================================
# POST-LOGIN NAVIGATION & PRECONDITIONS (New in v3.0)
# ============================================================

# Where to navigate after successful login
# Leave blank to stay on the page the app lands on after login
FEATURE_URL=https://yourapp.com/dashboard

# UI setup steps to run before EVERY test
# JSON array of natural language descriptions
# Example for a tag filter feature:
PRECONDITION_STEPS=["Click the Filter button to open the filter panel", "Expand the Tags section inside the filter panel"]

# Example for e-commerce checkout:
# PRECONDITION_STEPS=["Add a product to the cart", "Click Proceed to Checkout"]

# Example for CRM:
# PRECONDITION_STEPS=["Click the New Lead button", "Fill in Company Name with Test Corp"]

# ============================================================
# BROWSER SETTINGS (Recommended for debugging)
# ============================================================

# Set to false to see the browser during test execution
HEADLESS=false
```

### Step 4: Run your tests
```bash
python main.py
```

At the end, you'll see token usage summary:
```
========================================================================
  TOKEN USAGE SUMMARY
========================================================================
  AGENT                            CALLS    PROMPT     COMPL     TOTAL      COST
  -----------------------------------------------------------------------
  RequirementsAgent                   16     8,432     2,841    11,273   $0.0494
  TestDesignerAgent                   22    19,850     8,920    28,770   $0.1386
  ReviewerAgent                       22     9,210     1,840    11,050   $0.0415
  -----------------------------------------------------------------------
  TOTAL                               60    37,492    13,601    51,093   $0.2295
========================================================================
```

---

## 📋 Files Changed - Detailed Breakdown

### 🆕 NEW FILE
- **`utils/token_tracker.py`**
  - Global singleton for tracking OpenAI API token usage
  - Per-agent breakdown with call counts
  - Cost estimation based on gpt-4o pricing
  - Formatted summary table

### 🔧 UPDATED FILES

#### `agents/requirements_agent.py`
**Changes:**
- Import: `from utils.token_tracker import token_tracker`
- Added: `token_tracker.record("RequirementsAgent", response)` after API call

#### `agents/reviewer_agent.py`
**Changes:**
- Import: `from utils.token_tracker import token_tracker`
- Added: `token_tracker.record("ReviewerAgent", response)` after API call

#### `agents/test_designer_agent.py`
**Changes (5 major updates):**
1. **Bug fix:** `.first` added to login button locator to fix strict mode violation
2. **Token tracking:** `token_tracker.record("TestDesignerAgent", response)` added
3. **Login navigation:** `_LOGIN_HELPER` now navigates to `FEATURE_URL` after authentication
4. **Precondition system:** New `_PRECONDITION_HELPER_TEMPLATE` generates UI setup code
5. **System prompt:** Enforces mandatory `_login(page)` → `_precondition(page)` call sequence
6. **Prompt building:** Shows precondition steps prominently to the LLM
7. **Script assembly:** Every generated test includes the precondition helper function

#### `main.py`
**Changes:**
- Import: `from utils.token_tracker import token_tracker`
- Added: `token_tracker.reset()` at start of `run_from_csv_stories()` and `run_from_excel()`
- Added: `token_tracker.print_summary()` at end of `_print_summary()`

#### `config/settings.py`
**New settings:**
```python
FEATURE_URL: str = ""          # Where to navigate after login
PRECONDITION_STEPS: str = "[]" # JSON array of UI setup steps
```

#### `executors/test_executor.py`
**Bug fixes:**
1. **Import fix:** `cwd` changed from `reports/` to project root so `config` module is importable
2. **Defense-in-depth:** Added `sys.path.insert(0, project_root)` in test file headers
3. **Browser type fix:** Uses `settings.BROWSER_TYPE` instead of hardcoded `chromium`

---

## 🎯 What Each Update Solves

### Problem 1: Tests failing with "ModuleNotFoundError: No module named 'config'"
**Root cause:** Test executor ran subprocess from `reports/` folder, couldn't find `config` package  
**Solution:** Changed `cwd` to project root + added `sys.path` injection  
**Files:** `executors/test_executor.py`

### Problem 2: "strict mode violation: get_by_role resolved to 2 elements"
**Root cause:** Login page had multiple buttons matching the login pattern  
**Solution:** Added `.first` to login button locator  
**Files:** `agents/test_designer_agent.py`

### Problem 3: No visibility into token usage and API costs
**Root cause:** No tracking system for OpenAI API calls  
**Solution:** Global token tracker with per-agent breakdown and cost estimation  
**Files:** `utils/token_tracker.py` + all 3 agent files + `main.py`

### Problem 4: Tests couldn't handle multi-step UI setup (e.g. open filter panel, expand tags)
**Root cause:** Only had `_login()` helper, no concept of "get to the right UI state"  
**Solution:** Added `FEATURE_URL` + `PRECONDITION_STEPS` + auto-generated `_precondition()` helper  
**Files:** `config/settings.py`, `agents/test_designer_agent.py`

---

## ✨ Key Features of the Precondition System

### Completely Generic - Works for ANY Application

The precondition system is **not hardcoded for any specific app**. Change only `.env` — zero code changes needed.

**Example 1: E-commerce**
```bash
FEATURE_URL=https://shop.example.com/cart
PRECONDITION_STEPS=["Add product to cart", "Click Proceed to Checkout"]
```

**Example 2: CRM**
```bash
FEATURE_URL=https://crm.company.com/leads
PRECONDITION_STEPS=["Click New Lead button", "Fill Company Name with Test Corp"]
```

**Example 3: Banking**
```bash
FEATURE_URL=https://bank.example.com/transfers
PRECONDITION_STEPS=["Click Wire Transfer tab", "Select International Transfers"]
```

### How It Works

1. You define steps in **plain English** in `.env`
2. The `_build_precondition_helper()` method generates a `_precondition(page)` function
3. The LLM is **mandated** to call it before any test steps
4. Every generated test follows this pattern:
```python
def test_something(page):
    try:
        _login(page)           # authenticates + navigates to FEATURE_URL
        _precondition(page)    # executes all PRECONDITION_STEPS
        # ... actual test steps for this specific scenario ...
    except Exception:
        page.screenshot(path="failure_test_something.png")
        raise
```

---

## 🔍 Troubleshooting

### Tests still failing?
1. **Check HEADLESS setting** - Set to `false` to see what's happening in the browser
2. **Check FEATURE_URL** - Make sure it's the exact URL after login
3. **Check PRECONDITION_STEPS** - Verify the button/element names match your app
4. **Check logs** - Look at `qa_agent.log` for detailed error messages

### Token costs too high?
1. Check the summary to see which agent uses the most tokens
2. Consider using `gpt-4o-mini` for Requirements/Reviewer agents
3. Reduce `MAX_RETRY_LOOPS` in settings if tests are retrying too much

### Preconditions not working?
1. The LLM converts your descriptions to Playwright code
2. If element names are wrong, update `PRECONDITION_STEPS` in `.env`
3. Check generated test files in `reports/` to see what Playwright code was produced
4. Use specific element names (e.g. "Filter" not "the filter thing")

---

## 📊 Token Usage Details

The token tracker automatically:
- Records every OpenAI API call from all 3 agents
- Tracks prompt tokens, completion tokens, and total
- Counts how many times each agent was called
- Estimates cost based on current OpenAI pricing
- Displays a formatted summary at the end of each run

**No configuration needed** - it works automatically once files are installed.

---

## 🆘 Support

If you encounter issues:
1. Check that all 7 files were copied correctly
2. Verify your `.env` file has the new settings
3. Run with `HEADLESS=false` to see browser interactions
4. Check `qa_agent.log` for detailed error messages
5. Verify Python dependencies are installed: `pip install playwright openai openpyxl pydantic-settings`

---

## 📜 Version History

**v3.0** (Feb 18, 2026)
- Added token usage tracking system
- Added precondition system for multi-step UI setup
- Fixed ModuleNotFoundError import issues
- Fixed strict mode violations in login
- Fixed hardcoded browser type

**v2.x** (Previous)
- Multi-agent pipeline with retry logic
- Excel test case parsing
- CSV story import

---

## ✅ Verification Checklist

After installation, verify everything works:

- [ ] All 7 files copied to correct locations
- [ ] `.env` file updated with `FEATURE_URL` and `PRECONDITION_STEPS`
- [ ] `python main.py` runs without import errors
- [ ] Token usage summary appears at the end of the run
- [ ] Tests execute and browser opens (if `HEADLESS=false`)
- [ ] Generated tests include `_login()` and `_precondition()` calls

---

**Questions?** Check the main project documentation or review the inline comments in each file.
