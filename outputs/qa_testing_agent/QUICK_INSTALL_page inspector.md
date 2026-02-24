# Page Inspection - Quick Install

**Problem:** Tests fail because LLM guesses at selectors → wrong elements → timeouts  
**Solution:** Capture REAL selectors from your actual page → tests use exact IDs/classes → tests pass

---

## 📦 What's Included

```
page_inspector_agent.py         (NEW) - Captures real DOM
test_designer_agent.py          (UPDATED) - Uses real selectors
orchestrator.py                 (UPDATED) - Runs inspection
settings.py                     (UPDATED) - ENABLE_PAGE_INSPECTION flag
PAGE_INSPECTION_GUIDE.md        (NEW) - Full documentation
```

---

## ⚡ 3-Step Install

### 1. Copy Files
```bash
cp page_inspector_agent.py your_project/agents/
cp test_designer_agent.py your_project/agents/
cp orchestrator.py your_project/
cp settings.py your_project/config/
```

### 2. Update .env
Make sure these are set:
```bash
FEATURE_URL=https://dev.mirrix.app/assets
PRECONDITION_STEPS=["Click the Filter button", "Expand the Tags section"]
HEADLESS=false  # Recommended for first run
ENABLE_PAGE_INSPECTION=true  # Optional - enabled by default
```

### 3. Run
```bash
python main.py
```

---

## ✅ What You'll See

```
======================================================================
PAGE INSPECTION - Capturing real DOM selectors
======================================================================
...
✓ Page inspection successful
  - Captured 15 tag elements
  - Captured 8 buttons
  - Filter panel selector: .filter-sidebar
  Tests will use REAL selectors from your application
======================================================================

[1/16] Processing test case
...
```

---

## 🎯 How It Works

```
Pipeline starts
    ↓
Inspector logs in → navigates to /assets → runs preconditions
    ↓
Captures: Filter panel class="filter-sidebar"
          Tags: ["Vehicles", "Flower", "toys", ...]
          Buttons: ["Clear Search", "Save Search", ...]
    ↓
Test Designer receives real selectors
    ↓
Generates: page.locator(".filter-sidebar").click()  # ✅ Real selector
           page.get_by_text("Vehicles").click()      # ✅ Real tag name
    ↓
Tests execute successfully (no timeouts!)
```

---

## 🐛 Troubleshooting

**"Page inspection failed"**
- Check FEATURE_URL is correct
- Verify login credentials
- Run with HEADLESS=false to see what's happening

**"No selectors captured"**
- Your page uses different selectors than expected
- Check PAGE_INSPECTION_GUIDE.md for customization
- Fallback selectors still work

**Tests still timing out**
- Check that PRECONDITION_STEPS correctly opens filter panel
- Verify FEATURE_URL goes to the right page
- Inspect logs to see what selectors were captured

---

## 📖 Full Documentation

See **PAGE_INSPECTION_GUIDE.md** for:
- Detailed explanation
- Advanced configuration
- Troubleshooting guide
- Customization options

---

**That's it!** No more selector guessing. Tests use real IDs from your actual page. 🎉
