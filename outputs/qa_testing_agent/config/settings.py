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
    
    # Selenium/Playwright Config
    BROWSER_TYPE: str = "chrome"  # or "firefox", "webkit"
    HEADLESS: bool = False
    SCREENSHOT_ON_FAILURE: bool = True
    IMPLICIT_WAIT: int = 10
    
    # Agent Config
    MAX_RETRY_LOOPS: int = 3
    INCLUDE_MOCK_DATA_GENERATION: bool = True
    PARALLEL_EXECUTION: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
