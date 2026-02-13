"""
Test Executor - Executes generated test code
"""
import logging
import os
import subprocess
import tempfile
import sys
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from models import GeneratedTestCase, TestExecutionResult
from config.settings import TestStatus, settings

logger = logging.getLogger(__name__)

class TestExecutor:
    """Executes generated test code using pytest"""
    
    def __init__(self, output_dir: str = "./test_execution"):
        self.output_dir = output_dir
        self.screenshots_dir = os.path.join(output_dir, "screenshots")
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure output directories exist"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)
    
    def execute(self, generated_test: GeneratedTestCase) -> TestExecutionResult:
        """
        Execute a single generated test
        
        Args:
            generated_test: Generated test case with code
            
        Returns:
            TestExecutionResult
        """
        test_name = generated_test.test_case_id.replace("/", "_").replace(" ", "_")
        test_file = os.path.join(self.output_dir, f"test_{test_name}.py")
        
        start_time = datetime.now()
        
        try:
            # Write test code to file
            self._write_test_file(test_file, generated_test)
            
            # Execute test with pytest
            html_report = os.path.join(
                self.output_dir, 
                f"report_{test_name}.html"
            )
            
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_file,
                f"--html={html_report}",
                "--self-contained-html",
                "--tb=short",
                "-v",
                "-s"
            ], capture_output=True, text=True, timeout=settings.TEST_TIMEOUT_SECONDS)
            
            # Parse results
            success = result.returncode == 0
            
            # Extract screenshot path if failure
            screenshot_path = None
            if not success and settings.SCREENSHOT_ON_FAILURE:
                screenshot_path = self._extract_screenshot_path(result.stdout)
            
            execution_result = TestExecutionResult(
                test_case_id=generated_test.test_case_id,
                test_name=test_name,
                status=TestStatus.PASSED if success else TestStatus.FAILED,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error_message=result.stderr if not success else None,
                screenshot_path=screenshot_path,
                logs=[result.stdout, result.stderr]
            )
            
            logger.info(
                f"Test execution completed: {test_name} - "
                f"{'PASSED' if success else 'FAILED'}"
            )
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timed out: {test_name}")
            return TestExecutionResult(
                test_case_id=generated_test.test_case_id,
                test_name=test_name,
                status=TestStatus.FAILED,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error_message="Test execution timed out"
            )
            
        except Exception as e:
            logger.error(f"Error executing test: {str(e)}")
            return TestExecutionResult(
                test_case_id=generated_test.test_case_id,
                test_name=test_name,
                status=TestStatus.FAILED,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error_message=str(e)
            )
    
    def execute_batch(self, generated_tests: List[GeneratedTestCase]) -> List[TestExecutionResult]:
        """Execute multiple tests"""
        results = []
        
        for idx, test in enumerate(generated_tests, 1):
            logger.info(f"\n[{idx}/{len(generated_tests)}] Executing test")
            result = self.execute(test)
            results.append(result)
        
        return results
    
    def _write_test_file(self, filepath: str, generated_test: GeneratedTestCase) -> None:
        """Write generated test code to file"""
        # Add necessary imports and fixtures
        fixture_code = self._generate_fixture_code(generated_test)
        
        full_code = f"""import pytest
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path

logger = logging.getLogger(__name__)

# Test Data
TEST_DATA = {generated_test.test_data}
BASE_URL = TEST_DATA.get("base_url", "")

{fixture_code}

# Generic locator helpers
def _first_visible(driver, locators, timeout=10):
    for by, value in locators:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        except Exception:
            continue
    return None

def find_input(driver, label: str, timeout=10):
    label_l = label.lower()
    candidates = [
        (By.ID, label),
        (By.NAME, label),
        (By.NAME, label_l),
        (By.CSS_SELECTOR, f"input[aria-label*='{label}']"),
        (By.CSS_SELECTOR, f"input[placeholder*='{label}']"),
        (By.XPATH, f\"//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{label_l}')]/following::input[1]\"),
        (By.XPATH, f\"//input[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{label_l}')]\"),
        (By.XPATH, f\"//input[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{label_l}')]\"),
        (By.XPATH, f\"//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{label_l}')]\"),
    ]
    return _first_visible(driver, candidates, timeout=timeout)

def click_button(driver, text: str, timeout=10):
    text_l = text.lower()
    candidates = [
        (By.ID, text),
        (By.NAME, text),
        (By.XPATH, f\"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{text_l}')]\"),
        (By.XPATH, f\"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{text_l}')]\"),
        (By.XPATH, f\"//*[@role='button' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{text_l}')]\"),
    ]
    el = _first_visible(driver, candidates, timeout=timeout)
    if el:
        el.click()
        return True
    return False

# Generated Test Code
{generated_test.test_code}
"""
        
        with open(filepath, 'w') as f:
            f.write(full_code)
        
        logger.info(f"Test file written: {filepath}")
    
    def _generate_fixture_code(self, generated_test: GeneratedTestCase) -> str:
        """Generate pytest fixtures"""
        fixtures = f"""@pytest.fixture
def browser():
    \"\"\"Initialize webdriver\"\"\"
    browser_type = "{settings.BROWSER_TYPE}".lower()
    
    if browser_type in ["chrome", "chromium"]:
        options = webdriver.ChromeOptions()
        if {settings.HEADLESS}:
            options.add_argument("--headless")
        if "{settings.CHROME_BINARY}":
            options.binary_location = "{settings.CHROME_BINARY}"
        driver = webdriver.Chrome(options=options)
    elif browser_type == "firefox":
        options = webdriver.FirefoxOptions()
        if {settings.HEADLESS}:
            options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
    else:
        raise ValueError(f"Unsupported BROWSER_TYPE: {settings.BROWSER_TYPE}")
    
    driver.implicitly_wait({settings.IMPLICIT_WAIT})
    
    yield driver
    
    driver.quit()

@pytest.fixture
def logger_fixture():
    \"\"\"Setup logger\"\"\"
    return logger
"""
        return fixtures
    
    def _extract_screenshot_path(self, output: str) -> str:
        """Extract screenshot path from pytest output"""
        # This is a placeholder - actual implementation would parse output
        return os.path.join(self.screenshots_dir, "failure_screenshot.png")
