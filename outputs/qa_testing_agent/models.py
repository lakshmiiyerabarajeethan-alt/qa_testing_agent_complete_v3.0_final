"""
Data models for test cases and results
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from config.settings import RejectionReason, TestStatus

class TestStep(BaseModel):
    """Represents a single test step"""
    step_no: int
    description: str
    expected_results: str
    actual_results: Optional[str] = None
    status: TestStatus = TestStatus.PENDING

class TestCase(BaseModel):
    """Represents a test case from Excel"""
    test_scenario: str
    test_case_name: str
    test_data: Optional[Dict[str, Any]] = None
    steps: List[TestStep]
    remarks: Optional[str] = None

class RequirementsAnalysis(BaseModel):
    """Output from Requirements Analysis Agent"""
    test_case_id: str
    scenario_understanding: str
    identified_requirements: List[str]
    test_data_needs: Dict[str, Any]
    assumptions: List[str]
    analysis_timestamp: datetime = datetime.now()

class GeneratedTestCase(BaseModel):
    """Output from Test Designer Agent"""
    test_case_id: str
    test_code: str  # Generated Python/Selenium code
    test_data: Dict[str, Any]  # Generated mock data
    fixtures: List[str]  # Required fixtures
    parameterization: Optional[Dict[str, List[Any]]] = None
    estimated_duration_seconds: int
    generation_timestamp: datetime = datetime.now()

class ReviewResult(BaseModel):
    """Output from Reviewer Agent"""
    test_case_id: str
    is_approved: bool
    rejection_reason: RejectionReason = RejectionReason.NONE
    rejection_details: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    review_timestamp: datetime = datetime.now()

class TestExecutionResult(BaseModel):
    """Result of a single test execution"""
    test_case_id: str
    test_name: str
    status: TestStatus
    duration_seconds: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    logs: List[str] = []
    execution_timestamp: datetime = datetime.now()

class TestSuiteResult(BaseModel):
    """Overall test suite execution result"""
    suite_id: str
    total_tests: int
    passed_count: int
    failed_count: int
    rejected_count: int
    test_results: List[TestExecutionResult]
    rejection_details: List[Dict[str, Any]] = []  # For rejected test cases
    html_report_path: Optional[str] = None
    execution_start: datetime
    execution_end: datetime = datetime.now()
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_count / self.total_tests) * 100
