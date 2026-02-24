"""
config/settings.py — Generic QA Agent Configuration
====================================================
ALL application-specific values live in .env (or environment variables).
Changing the target application requires only a .env change — no code changes.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from enum import Enum


class TestStatus(str, Enum):
    PENDING  = "PENDING"
    PASSED   = "PASSED"
    FAILED   = "FAILED"
    SKIPPED  = "SKIPPED"
    REJECTED = "REJECTED"


class RejectionReason(str, Enum):
    NONE         = "NONE"
    DATA_ISSUE   = "DATA_ISSUE"
    UI_CHANGE    = "UI_CHANGE"
    MISMATCH     = "MISMATCH"


class Settings(BaseSettings):

    # ------------------------------------------------------------------
    # LLM / AI
    # ------------------------------------------------------------------
    OPENAI_API_KEY:   str = ""
    OPENAI_MODEL:     str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 0.3

    # ------------------------------------------------------------------
    # Target web application
    # Change these in .env to point at any web app — no code changes needed.
    # ------------------------------------------------------------------
    BASE_URL:       str = "https://example.com/login"
    LOGIN_EMAIL:    str = ""
    LOGIN_PASSWORD: str = ""

    # Login form field labels — override if the app uses different labels
    # e.g. EMAIL_FIELD_LABEL=Username for apps that use "Username" instead of "Email"
    EMAIL_FIELD_LABEL:      str = "Email"
    PASSWORD_FIELD_LABEL:   str = "Password"

    # Regex pattern for matching the login button (case-insensitive)
    # Matches: Login, Log in, Log In, Sign In, Sign in, Signin
    LOGIN_BUTTON_PATTERN:   str = r"log.?in|sign.?in"

    # ------------------------------------------------------------------
    # Post-login navigation & precondition steps
    # These define where to land after login and what UI setup to perform
    # before the actual test steps run.  Change in .env — no code edits.
    # ------------------------------------------------------------------

    # URL to navigate to after successful login.
    # Leave blank to stay on whatever page the app lands on after login.
    # Example: FEATURE_URL=https://myapp.com/dashboard/assets
    FEATURE_URL: str = ""

    # Per-story preconditions mapping (JSON object)
    # Example (in .env — note the outer single quotes):
    #   STORY_PRECONDITIONS_JSON='{"Story Title A": ["Step 1", "Step 2"], "CSV-123": ["Step 1"]}'
    STORY_PRECONDITIONS_JSON: str = "{}"

    # ------------------------------------------------------------------
    # Browser / execution
    # ------------------------------------------------------------------
    BROWSER_TYPE:   str  = "chromium"    # chromium | firefox | webkit
    HEADLESS:       bool = True
    SCREENSHOT_ON_FAILURE: bool = True

    # Timeouts (milliseconds)
    ELEMENT_TIMEOUT_MS: int  = 10_000   # for expect().to_be_visible() etc.
    TEST_TIMEOUT_MS:    int  = 300_000  # per-test global timeout (5 min)

    # Seconds (used by TestExecutor subprocess runner)
    TEST_TIMEOUT_SECONDS: int = 300

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    MAX_RETRY_LOOPS:         int  = 3
    EXECUTE_REJECTED_TESTS:  bool = True
    PARALLEL_EXECUTION:      bool = False
    INCLUDE_MOCK_DATA_GENERATION: bool = True
    
    # Page Inspection - captures real DOM from the application
    # When enabled, the system logs in once, captures actual selectors,
    # and feeds them to the test generator for accurate element targeting.
    ENABLE_PAGE_INSPECTION:  bool = True

    # ------------------------------------------------------------------
    # Folder layout
    # ------------------------------------------------------------------
    TEST_INPUT_FOLDER:   str = "./test_inputs"
    REPORT_OUTPUT_FOLDER: str = "./reports"
    SCREENSHOTS_FOLDER:  str = "./reports/screenshots"
    UI_SNAPSHOT_FOLDER: str = "./ui_snapshot"
    SELECTOR_MAP_FILE: str = "selector_map.json"
    RECORDED_FLOW_FILE: str = "recorded_flow.py"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow loading from a file named _env too (your current convention)
        extra = "ignore"


settings = Settings(_env_file=[".env", "_env"])
