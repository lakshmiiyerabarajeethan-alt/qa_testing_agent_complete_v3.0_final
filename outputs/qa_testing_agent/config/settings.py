"""
Configuration module for QA Testing Agent
"""
import os
from enum import Enum
from pydantic_settings import BaseSettings

class RejectionReason(str, Enum):
    """Possible rejection reasons from reviewer"""
    DATA_ISSUE = "DATA_ISSUE"
    UI_CHANGE = "UI_CHANGE"
    REQUIREMENT_MISMATCH = "REQUIREMENT_MISMATCH"
    NONE = "NONE"

class TestStatus(str, Enum):
    """Test execution statuses"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"

class Settings(BaseSettings):
    """Configuration settings"""
    # OpenAI Config
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 2000
    
    # Project Config
    PROJECT_NAME: str = "QA Testing Agent"
    TEST_INPUT_FOLDER: str = "./test_inputs"
    REPORT_OUTPUT_FOLDER: str = "./reports"
    SCREENSHOTS_FOLDER: str = "./reports/screenshots"
    BASE_URL: str = os.getenv("BASE_URL", "")
    LOGIN_EMAIL: str = os.getenv("LOGIN_EMAIL", "")
    LOGIN_PASSWORD: str = os.getenv("LOGIN_PASSWORD", "")
    LOGIN_EMAIL_SELECTOR: str = os.getenv("LOGIN_EMAIL_SELECTOR", "")
    LOGIN_PASSWORD_SELECTOR: str = os.getenv("LOGIN_PASSWORD_SELECTOR", "")
    LOGIN_BUTTON_SELECTOR: str = os.getenv("LOGIN_BUTTON_SELECTOR", "")
    POST_LOGIN_SELECTOR: str = os.getenv("POST_LOGIN_SELECTOR", "")
    
    # Selenium/Playwright Config
    BROWSER_TYPE: str = "chrome"  # or "firefox", "webkit"
    HEADLESS: bool = False
    SCREENSHOT_ON_FAILURE: bool = True
    IMPLICIT_WAIT: int = 10
    CHROME_BINARY: str = os.getenv("CHROME_BINARY", "")
    TEST_TIMEOUT_SECONDS: int = int(os.getenv("TEST_TIMEOUT_SECONDS", "300"))
    
    # Agent Config
    MAX_RETRY_LOOPS: int = 3
    INCLUDE_MOCK_DATA_GENERATION: bool = True
    PARALLEL_EXECUTION: bool = False
    EXECUTE_REJECTED_TESTS: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
