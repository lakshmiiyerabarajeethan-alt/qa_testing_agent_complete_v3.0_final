# ✅ Quick Installation Checklist

Follow these steps to install the v3.0 update package.

---

## 📦 Before You Start

**What you need:**
- [ ] Your existing QA Testing Agent project
- [ ] This `updated_files` folder (downloaded)
- [ ] 5 minutes

**What this update includes:**
- ✅ Bug fixes (tests now execute, browser visible option works)
- ✅ Token usage tracking (see API costs per agent)
- ✅ Precondition system (handle multi-step UI setup)

---

## 🚀 Installation Steps

### 1️⃣ Backup (Optional but Recommended)
```bash
cd your_qa_project/
mkdir backup_$(date +%Y%m%d)
cp agents/*.py backup_*/
cp executors/*.py backup_*/
cp config/*.py backup_*/
cp main.py backup_*/
```
✅ Done

---

### 2️⃣ Copy Files
```bash
# From the directory containing 'updated_files' folder:
cp -r updated_files/agents/* your_qa_project/agents/
cp -r updated_files/utils/* your_qa_project/utils/
cp -r updated_files/config/* your_qa_project/config/
cp -r updated_files/executors/* your_qa_project/executors/
cp updated_files/main.py your_qa_project/
```

**Or manually copy these 7 files:**
- [ ] `utils/token_tracker.py` (NEW file)
- [ ] `agents/requirements_agent.py`
- [ ] `agents/reviewer_agent.py`
- [ ] `agents/test_designer_agent.py`
- [ ] `executors/test_executor.py`
- [ ] `config/settings.py`
- [ ] `main.py`

✅ Done

---

### 3️⃣ Update .env File

Open your `.env` or `_env` file and add these lines at the end:

```bash
# ============================================================
# POST-LOGIN NAVIGATION & PRECONDITIONS (New in v3.0)
# ============================================================
FEATURE_URL=
PRECONDITION_STEPS=[]
```

**For your tag filter tests, update to:**
```bash
FEATURE_URL=https://yourapp.com/assets
PRECONDITION_STEPS=["Click the Filter button to open the filter panel", "Expand the Tags section inside the filter panel"]
```

**Optional - to see the browser during tests:**
```bash
HEADLESS=false
```

✅ Done

---

### 4️⃣ Test Installation

```bash
cd your_qa_project/
python main.py
```

**What to check:**
- [ ] Script runs without import errors
- [ ] At the end, you see a "TOKEN USAGE SUMMARY" table
- [ ] If `HEADLESS=false`, browser opens visibly
- [ ] Tests execute successfully

✅ Done

---

## 🎯 Success Indicators

At the end of the run, you should see:

```
========================================================================
EXECUTION SUMMARY
========================================================================
Duration: 120.45s
Total Tests: 16 (Approved: 16, Rejected: 0)
Results: Passed: 14, Failed: 2, Rate: 87.5%
========================================================================

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
  Prices: gpt-4o $2.50/1M prompt · $10.00/1M completion (est.)
========================================================================
```

✅ Token summary appears = Installation successful!

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'utils'"
**Solution:** The `utils/` folder must exist in your project root.
```bash
mkdir -p utils
cp updated_files/utils/token_tracker.py utils/
```

### "No token summary at the end"
**Check:** Did you copy all 5 files that import token_tracker?
- agents/requirements_agent.py
- agents/reviewer_agent.py  
- agents/test_designer_agent.py
- main.py
- utils/token_tracker.py

### "Tests still failing at login"
**Solution:** 
1. Set `HEADLESS=false` to see what's happening
2. Check your `LOGIN_EMAIL` and `LOGIN_PASSWORD` in .env
3. Verify `BASE_URL` points to the login page

### "Browser doesn't open"
**Solution:** Set `HEADLESS=false` in .env file

---

## 📖 Next Steps

1. **Read README.md** - Full documentation of all features
2. **Read CHANGES.md** - Detailed list of what changed in each file
3. **Configure preconditions** - Update `PRECONDITION_STEPS` for your app
4. **Monitor token usage** - Watch the summary to optimize costs

---

## 🆘 Need Help?

1. Check `README.md` in this folder
2. Check `CHANGES.md` for detailed change documentation
3. Review `.env.template` for all available settings
4. Check `qa_agent.log` for detailed error messages

---

## ✅ Installation Complete!

You're now running v3.0 with:
- ✅ Fixed import errors
- ✅ Fixed strict mode login issues
- ✅ Token usage tracking
- ✅ Generic precondition system
- ✅ Visible browser option

**Happy testing! 🎉**
