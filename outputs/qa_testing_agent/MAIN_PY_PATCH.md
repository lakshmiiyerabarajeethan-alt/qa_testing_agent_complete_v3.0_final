# main.py Patch Instructions

## 1. Fix logging (prevents UnicodeEncodeError on Windows)

Replace this block at the top of main.py:
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qa_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
```

With:
```python
from logging_setup import setup_logging
setup_logging()
```

## 2. Screenshots in HTML report

Screenshots are now stored as relative paths (`screenshots/name.png`) in
`TestExecutionResult.screenshot_path`. This means the HTML report can link
to them correctly since the report is in the same `reports/` folder.

No changes needed to report_generator.py - it already uses whatever string
is in `screenshot_path` as the href. With relative paths it now works.

## 3. Headless mode

In your `.env` file:
```
HEADLESS=False    # Browser visible - you can watch test execution
HEADLESS=True     # Headless - faster, no window
```

When headless=False, you should see the browser open AND the test executing.
If browser opens but nothing happens, it means the test crashed immediately
on the first line - check the _run_*.py file and the error in the report.
