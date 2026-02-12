"""
Example: Testing the QA Agent End-to-End
Demonstrates how to use the system with sample test cases
"""

from models import TestCase, TestStep
from config.settings import TestStatus
from generators.mock_data_generator import MockDataGenerator
from agents.requirements_agent import RequirementsAnalysisAgent
from agents.test_designer_agent import TestDesignerAgent
from agents.reviewer_agent import ReviewerAgent
from orchestrator import QATestingOrchestrator
from executors.test_executor import TestExecutor
from utils.report_generator import HTMLReportGenerator
import json

def example_create_test_case():
    """Create a sample test case"""
    test_case = TestCase(
        test_scenario="Login",
        test_case_name="login_to_Metsa_WebUI",
        test_data=None,
        steps=[
            TestStep(
                step_no=1,
                description="Enter metsaco-sandbox-step.mdm.stibosystems.com url to search bar",
                expected_results="Metsaco-sandbox web ui should load"
            ),
            TestStep(
                step_no=2,
                description="Log into the UI with valid credentials",
                expected_results="User should navigate to the homepage for Web UI"
            ),
            TestStep(
                step_no=3,
                description="Click on the Customer Data Harmonization link",
                expected_results="User should access the Customer Data Harmonization WEB UI screen"
            ),
        ]
    )
    return test_case

def example_generate_mock_data():
    """Example of mock data generation"""
    generator = MockDataGenerator()
    
    # Generate login credentials
    credentials = generator.generate_user_credentials()
    print("\n=== Generated Login Credentials ===")
    print(json.dumps(credentials, indent=2))
    
    # Generate customer data
    customer = generator.generate_customer_data()
    print("\n=== Generated Customer Data ===")
    print(json.dumps(customer, indent=2))
    
    # Generate scenario-specific data
    login_data = generator.generate_test_data_for_scenario("Login Test")
    print("\n=== Generated Login Test Data ===")
    print(json.dumps(login_data, indent=2))

def example_agent_workflow():
    """Example of multi-agent workflow"""
    # Create a test case
    test_case = example_create_test_case()
    
    print("\n=== Test Case Created ===")
    print(f"Scenario: {test_case.test_scenario}")
    print(f"Name: {test_case.test_case_name}")
    print(f"Steps: {len(test_case.steps)}")
    
    # Phase 1: Requirements Analysis
    print("\n=== Phase 1: Requirements Analysis ===")
    requirements_agent = RequirementsAnalysisAgent()
    requirements = requirements_agent.analyze(test_case)
    
    print(f"Scenario Understanding:\n{requirements.scenario_understanding}")
    print(f"\nIdentified Requirements:")
    for req in requirements.identified_requirements:
        print(f"  - {req}")
    print(f"\nTest Data Needs:")
    print(json.dumps(requirements.test_data_needs, indent=2))
    
    # Phase 2: Test Design
    print("\n=== Phase 2: Test Design ===")
    designer_agent = TestDesignerAgent()
    generated_test = designer_agent.design_test(test_case, requirements)
    
    print(f"Test Case ID: {generated_test.test_case_id}")
    print(f"Generated Code Length: {len(generated_test.test_code)} characters")
    print(f"Test Data Generated: {list(generated_test.test_data.keys())}")
    print(f"Fixtures: {', '.join(generated_test.fixtures)}")
    print(f"Estimated Duration: {generated_test.estimated_duration_seconds}s")
    
    # Phase 3: Review
    print("\n=== Phase 3: Review ===")
    reviewer_agent = ReviewerAgent()
    review_result = reviewer_agent.review(test_case, requirements, generated_test)
    
    print(f"Approved: {'Yes' if review_result.is_approved else 'No'}")
    if not review_result.is_approved:
        print(f"Rejection Reason: {review_result.rejection_reason}")
        print(f"Details: {review_result.rejection_details}")
        print(f"Suggestions: {review_result.improvement_suggestions}")

def example_full_orchestration():
    """Example of full orchestration with multiple test cases"""
    # Create multiple test cases
    test_cases = [
        example_create_test_case(),
        TestCase(
            test_scenario="Customer Management",
            test_case_name="create_new_customer",
            steps=[
                TestStep(
                    step_no=1,
                    description="Navigate to Customer Management screen",
                    expected_results="Customer Management screen loads"
                ),
                TestStep(
                    step_no=2,
                    description="Click on 'Create New Customer' button",
                    expected_results="Create Customer form opens"
                ),
                TestStep(
                    step_no=3,
                    description="Fill in customer details and submit",
                    expected_results="New customer created successfully"
                ),
            ]
        ),
    ]
    
    print(f"\n=== Processing {len(test_cases)} Test Cases ===\n")
    
    # Run orchestrator
    orchestrator = QATestingOrchestrator()
    results = orchestrator.process_test_suite(test_cases)
    
    print(f"\n=== Processing Complete ===")
    print(f"Total Results: {len(results)}")
    
    for idx, (generated_test, review_result, rejection_history) in enumerate(results, 1):
        print(f"\n[{idx}] {generated_test.test_case_id}")
        print(f"  Approved: {'Yes' if review_result.is_approved else 'No'}")
        if not review_result.is_approved and rejection_history:
            print(f"  Rejection Attempts: {len(rejection_history)}")
            for attempt in rejection_history:
                print(f"    - Attempt {attempt['attempt']}: {attempt['reason']}")

def example_execution_and_reporting():
    """Example of test execution and report generation"""
    # This would execute approved tests and generate reports
    print("\n=== Test Execution and Reporting Example ===")
    print("In production, this would:")
    print("  1. Execute approved test cases")
    print("  2. Collect execution results")
    print("  3. Generate comprehensive HTML report")
    print("  4. Include screenshots on failure")
    print("  5. Track metrics (pass rate, coverage, etc.)")
    print("  6. Document rejection reasons")

if __name__ == "__main__":
    print("="*70)
    print("QA TESTING AGENT - EXAMPLES")
    print("="*70)
    
    # Example 1: Create test case
    print("\n[EXAMPLE 1] Creating Test Case")
    print("-" * 70)
    example_create_test_case()
    
    # Example 2: Generate mock data
    print("\n[EXAMPLE 2] Generating Mock Data")
    print("-" * 70)
    example_generate_mock_data()
    
    # Example 3: Agent workflow
    print("\n[EXAMPLE 3] Multi-Agent Workflow")
    print("-" * 70)
    print("\nNote: This requires OPENAI_API_KEY to be set")
    print("Uncomment to run:")
    # example_agent_workflow()
    
    # Example 4: Full orchestration
    print("\n[EXAMPLE 4] Full Test Suite Orchestration")
    print("-" * 70)
    print("Note: This requires OPENAI_API_KEY to be set")
    print("Uncomment to run:")
    # example_full_orchestration()
    
    # Example 5: Execution and reporting
    print("\n[EXAMPLE 5] Execution and Reporting")
    print("-" * 70)
    example_execution_and_reporting()
    
    print("\n" + "="*70)
    print("To run the full pipeline, use: python main.py")
    print("="*70)
