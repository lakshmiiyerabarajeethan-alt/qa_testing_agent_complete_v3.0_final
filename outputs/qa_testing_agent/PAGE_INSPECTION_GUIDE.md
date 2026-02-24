# Page Inspector Agent - Real DOM Selector Capture

**Version:** 4.0  
**What it solves:** Tests failing because the LLM guesses at selectors instead of using real ones from your application.

---

## 🎯 The Problem This Solves

**Before Page Inspection:**
```python
# Test Designer GUESSES at selectors:
page.locator("[data-testid='filter-panel']").click()  # ❌ Doesn't exist
page.get_by_text("Tag A").click()                      # ❌ Wrong locator
```

**After Page Inspection:**
```python
# Test Designer uses REAL selectors from your page:
page.locator(".filter-sidebar").click()                # ✅ Actual class from DOM
page.get_by_text("Vehicles").click()                   # ✅ Real tag name from page
```

---

## 🚀 How It Works

```
Pipeline Start
    ↓
┌─────────────────────────────────────┐
│ 1. Page Inspector Agent launches   │
│    - Logs into application          │
│    - Navigates to FEATURE_URL       │
│    - Executes PRECONDITION_STEPS    │
│    - Captures real DOM elements     │
└─────────────────────────────────────┘
    ↓
    Captures:
    - Filter panel: <div class="filter-sidebar">
    - Tags section: <div class="tag-list">
    - Tag items: ["Vehicles", "Flower", "toys", ...]
    - Buttons: ["Clear Search", "Save Search", ...]
    ↓
┌─────────────────────────────────────┐
│ 2. Test Designer Agent receives:   │
│    "Filter Panel: .filter-sidebar"  │
│    "Tags: Vehicles, Flower, toys"   │
│    "Buttons: Clear Search, ..."     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. Generates tests with REAL IDs    │
│    from your actual application     │
└─────────────────────────────────────┘
    ↓
✅ Tests execute successfully
```

---

## 📦 What's New in This Update

### New Files
```
agents/
  └── page_inspector_agent.py    (NEW) - Captures DOM from your app
```

### Updated Files
```
agents/test_designer_agent.py    - Now receives real selectors
orchestrator.py                   - Runs inspection at pipeline start
config/settings.py                - Added ENABLE_PAGE_INSPECTION flag
```

---

## ⚙️ Installation

### Step 1: Copy Files
```bash
# Copy new file
cp page_inspector_agent.py your_project/agents/

# Replace updated files
cp test_designer_agent.py your_project/agents/
cp orchestrator.py your_project/
cp settings.py your_project/config/
```

### Step 2: Update .env (Optional)
```bash
# Enable page inspection (default: true)
ENABLE_PAGE_INSPECTION=true

# Make sure these are configured:
FEATURE_URL=https://dev.mirrix.app/assets
PRECONDITION_STEPS=["Click the Filter button", "Expand the Tags section"]
HEADLESS=false  # Recommended - see what's happening
```

### Step 3: Run
```bash
python main.py
```

---

## 📊 What You'll See

When you run the pipeline with page inspection enabled:

```
======================================================================
PAGE INSPECTION - Capturing real DOM selectors
======================================================================
2026-02-18 11:30:15 - orchestrator - INFO - Starting page inspection...
2026-02-18 11:30:15 - orchestrator - INFO - Target: https://dev.mirrix.app/assets
2026-02-18 11:30:16 - page_inspector_agent - INFO - Step 1: Logging in...
2026-02-18 11:30:17 - page_inspector_agent - INFO - Login successful
2026-02-18 11:30:17 - page_inspector_agent - INFO - Step 2: Navigating to https://dev.mirrix.app/assets
2026-02-18 11:30:18 - page_inspector_agent - INFO - Step 3: Executing 2 precondition steps...
2026-02-18 11:30:18 - page_inspector_agent - INFO -   Precondition 1: Click the Filter button
2026-02-18 11:30:19 - page_inspector_agent - INFO -   Precondition 2: Expand the Tags section
2026-02-18 11:30:19 - page_inspector_agent - INFO - Step 4: Capturing page DOM...
2026-02-18 11:30:19 - page_inspector_agent - INFO - Found filter panel: class=filter-sidebar
2026-02-18 11:30:19 - page_inspector_agent - INFO - Found tags section: class=tag-list
2026-02-18 11:30:19 - page_inspector_agent - INFO - Found 15 tags using selector: .tag-item
2026-02-18 11:30:20 - page_inspector_agent - INFO - Page inspection completed successfully
2026-02-18 11:30:20 - orchestrator - INFO - ✓ Page inspection successful
2026-02-18 11:30:20 - orchestrator - INFO -   - Captured 15 tag elements
2026-02-18 11:30:20 - orchestrator - INFO -   - Captured 8 buttons
2026-02-18 11:30:20 - orchestrator - INFO -   - Filter panel selector: .filter-sidebar
2026-02-18 11:30:20 - orchestrator - INFO -   Tests will use REAL selectors from your application
======================================================================

[1/16] Processing test case
============================================================
Processing: auto_populate_tags_after_initial_selection
============================================================
...
```

---

## 🔍 How DOM Capture Works

The Page Inspector looks for elements using multiple strategies:

### 1. Filter Panel Detection
Tries in order:
- `[data-testid='filter-panel']`
- `[data-testid='filter-container']`
- `.filter-panel` (class)
- `#filter-panel` (id)

### 2. Tags Section Detection
Tries in order:
- `[data-testid='tags-section']`
- `.tags-section` (class)
- Finding heading with text "Tags"

### 3. Individual Tag Items
Tries in order:
- `[data-testid*='tag']` (any data-testid containing 'tag')
- `.tag-item` (class)
- `.tag` (class)
- `[role='button'][aria-label*='tag']`

### 4. Buttons, Inputs, Links
- Captures all interactive elements
- Records their text, aria-labels, and attributes

---

## 💡 Test Designer Receives This Context

When generating tests, the LLM sees:

```
REAL PAGE SELECTORS (from actual inspection):

Filter Panel: .filter-sidebar
Tags Section: .tag-list

Available Tags (15 found):
  - 'Vehicles' (use: page.get_by_text('Vehicles'))
  - 'Lakshmi1911' (use: page.get_by_text('Lakshmi1911'))
  - 'Flower' (use: page.get_by_text('Flower'))
  - 'toys' (use: page.get_by_text('toys'))
  - 'Bear' (use: page.get_by_text('Bear'))
  ...

Buttons on page (8 found):
  - 'Clear Search'
  - 'Save Search'
  - 'Export'
  - 'Filter'
  ...

USE THESE EXACT SELECTORS - they are from the real page, not guesses.
```

---

## ⚙️ Configuration Options

### Enable/Disable Page Inspection

**In .env:**
```bash
ENABLE_PAGE_INSPECTION=true   # Default: true
```

**Or in code:**
```python
from config.settings import settings
settings.ENABLE_PAGE_INSPECTION = False  # Disable
```

### Force Re-Inspection

By default, inspection runs once and caches results. To force refresh:

```python
from agents.page_inspector_agent import get_page_inspector

inspector = get_page_inspector()
inspector.clear_cache()  # Next call will re-inspect
dom_info = inspector.inspect(force_refresh=True)  # Or force directly
```

---

## 🐛 Troubleshooting

### "Page inspection failed"

**Possible causes:**
1. **Login failed** - Check `BASE_URL`, `LOGIN_EMAIL`, `LOGIN_PASSWORD`
2. **FEATURE_URL unreachable** - Verify URL is correct
3. **Preconditions failed** - Check `PRECONDITION_STEPS` descriptions

**How to debug:**
```bash
# Set HEADLESS=false to see browser
HEADLESS=false

# Check the logs
tail -f qa_agent.log
```

### "Could not find filter panel"

**Solution:** The inspector tries common selectors. If yours is different:

1. Run with `HEADLESS=false`
2. Watch the browser during inspection
3. Inspect your page manually to find the actual selector
4. The fallback still works - tests use generic locators

### "No tag elements captured"

**Cause:** Your tag elements use different selectors than expected.

**Solution:**
1. Inspect your page HTML
2. Find the actual class/id/data-testid for tags
3. Update `page_inspector_agent.py` line 267 to add your selector:

```python
selectors = [
    "[data-testid*='tag']",
    ".tag-item",
    ".tag",
    ".your-custom-tag-class",  # Add yours here
    "[role='button'][aria-label*='tag']",
]
```

---

## 📈 Performance Impact

**Inspection Time:** ~5-10 seconds (runs once per pipeline)

**Benefits:**
- ✅ Tests execute successfully on first try
- ✅ No more timeout failures due to wrong selectors
- ✅ Reduces retry loops and regeneration
- ✅ Overall pipeline completes faster

**Cost:** Minimal - inspection runs once, not per test

---

## 🔧 Advanced Usage

### Manual Inspection (Outside Pipeline)

```python
from agents.page_inspector_agent import PageInspectorAgent

inspector = PageInspectorAgent()
dom_info = inspector.inspect()

if dom_info["success"]:
    print(f"Filter panel: {dom_info['filter_panel']}")
    print(f"Tags found: {len(dom_info['tag_items'])}")
    
    for tag in dom_info['tag_items']:
        print(f"  - {tag['name']} → {tag['selector']}")
```

### Get Selector Summary

```python
from agents.page_inspector_agent import get_page_inspector

inspector = get_page_inspector()
inspector.inspect()  # Run inspection

summary = inspector.get_selector_summary()
print(summary)
```

Output:
```
REAL PAGE SELECTORS (from actual inspection):

Filter Panel: .filter-sidebar
Tags Section: .tag-list

Available Tags (15 found):
  - 'Vehicles' (use: page.get_by_text('Vehicles'))
  ...
```

### Access Raw DOM Data

```python
dom_info = inspector.inspect()

# Access captured data
filter_panel = dom_info["filter_panel"]
# {"selector": ".filter-sidebar", "type": "class", "value": "filter-sidebar"}

tags = dom_info["tag_items"]
# [{"name": "Vehicles", "selector": ".tag-item", "text": "Vehicles"}, ...]

buttons = dom_info["buttons"]
# [{"text": "Clear Search", "selector": "button:has-text('Clear Search')", "role": "button"}, ...]
```

---

## 🎛️ Customization

### Add Custom Selector Patterns

Edit `agents/page_inspector_agent.py`:

**For filter panel** (line 233):
```python
candidates = [
    ("data-testid", "filter-panel"),
    ("data-testid", "your-custom-testid"),  # Add yours
    ("class", "your-filter-class"),          # Add yours
]
```

**For tags** (line 267):
```python
selectors = [
    "[data-testid*='tag']",
    ".your-custom-tag-class",  # Add yours
]
```

---

## ✅ Verification

To verify page inspection is working:

1. **Check logs** for inspection phase:
   ```
   PAGE INSPECTION - Capturing real DOM selectors
   ✓ Page inspection successful
   ```

2. **Check test generation** - Look at generated test files in `reports/`:
   ```python
   # Should use real selectors like:
   page.locator(".filter-sidebar").click()
   page.get_by_text("Vehicles").click()
   
   # NOT generic guesses like:
   page.locator("[data-testid='filter-panel']").click()
   ```

3. **Check execution** - Tests should pass without timeout errors

---

## 🚀 Next Steps After Installation

1. **Run once with `HEADLESS=false`** to watch inspection
2. **Check logs** - Look for "Page inspection successful"
3. **Examine generated tests** - Verify real selectors are used
4. **Run tests** - Should execute without timeouts

---

## 📞 Troubleshooting Common Issues

| Issue | Solution |
|-------|----------|
| Import error: page_inspector_agent | Make sure file is in `agents/` folder |
| "Page inspection failed" | Check login credentials and FEATURE_URL |
| No selectors captured | Run with HEADLESS=false and inspect manually |
| Tests still timing out | Check that PRECONDITION_STEPS matches your UI flow |

---

**That's it!** Your tests now use real selectors from your actual application instead of guesses. 🎉
