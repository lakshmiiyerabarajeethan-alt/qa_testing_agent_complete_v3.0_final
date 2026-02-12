"""
Test Designer Agent
Generates test code using OpenAI
"""
import json
import logging
from typing import Optional
from openai import OpenAI
from models import TestCase, RequirementsAnalysis, GeneratedTestCase
from config.settings import settings
from generators.mock_data_generator import MockDataGenerator

logger = logging.getLogger(__name__)

class TestDesignerAgent:
    """Generates test code based on requirements"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.data_generator = MockDataGenerator()
    
    def design_test(self, 
                   test_case: TestCase, 
                   requirements: RequirementsAnalysis,
                   retry_context: Optional[str] = None) -> GeneratedTestCase:
        """
        Design and generate test code
        
        Args:
            test_case: Original test case
            requirements: Analysis from requirements agent
            retry_context: Context if retry due to rejection
            
        Returns:
            GeneratedTestCase with code and data
        """
        # Generate mock data
        test_data = self._generate_test_data(test_case, requirements)
        
        # Generate test code
        test_code = self._generate_test_code(test_case, requirements, test_data, retry_context)
        
        generated_test = GeneratedTestCase(
            test_case_id=f"{test_case.test_scenario}_{test_case.test_case_name}",
            test_code=test_code,
            test_data=test_data,
            fixtures=self._identify_fixtures(test_case, requirements),
            estimated_duration_seconds=len(test_case.steps) * 5
        )
        
        logger.info(f"Test design completed for {generated_test.test_case_id}")
        return generated_test
    
    def _generate_test_data(self, 
                           test_case: TestCase, 
                           requirements: RequirementsAnalysis) -> dict:
        """Generate mock data for the test"""
        test_data = {}
        
        # Use requirements-specified needs
        if requirements.test_data_needs:
            test_data.update(requirements.test_data_needs)
        
        # Generate scenario-specific data
        scenario_data = self.data_generator.generate_test_data_for_scenario(
            test_case.test_scenario
        )
        test_data.update(scenario_data)
        
        logger.info(f"Generated test data: {list(test_data.keys())}")
        return test_data
    
    def _generate_test_code(self,
                           test_case: TestCase,
                           requirements: RequirementsAnalysis,
                           test_data: dict,
                           retry_context: Optional[str] = None) -> str:
        """Generate test code using OpenAI"""
        steps_text = "\n".join([
            f"Step {step.step_no}: {step.description} => {step.expected_results}"
            for step in test_case.steps
        ])
        
        prompt = f"""Generate professional Selenium/Playwright test code in Python for this test case:

Test Scenario: {test_case.test_scenario}
Test Case: {test_case.test_case_name}

Requirements Understanding:
{requirements.scenario_understanding}

Test Steps:
{steps_text}

Test Data Available:
{json.dumps(test_data, indent=2)}

Generate ONLY the test code (class and methods) that:
1. Uses pytest framework
2. Includes proper setup/teardown with fixtures
3. Has explicit waits and error handling
4. Includes assertions for each step
5. Takes screenshots on failure
6. Uses the test_data provided
7. Has clear comments
8. Follows best practices for UI testing

Important: Return ONLY valid Python code, no markdown or explanations.
Use @pytest.fixture for setup/teardown.
Use WebDriverWait for explicit waits (Selenium) or context managers (Playwright).
"""
        
        if retry_context:
            prompt += f"\n\nREJECTION FEEDBACK:\n{retry_context}\nPlease improve the test code based on this feedback."
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert automation engineer specializing in UI testing.
                        Generate clean, professional, production-ready test code.
                        Always return valid Python code only - no markdown, no explanations."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # Lower temp for code generation
                max_tokens=2500
            )
            
            code = response.choices[0].message.content
            
            # Clean up markdown if present
            if code.startswith("```"):
                code = "\n".join(code.split("\n")[1:-1])
            
            logger.info(f"Generated test code ({len(code)} chars)")
            return code
            
        except Exception as e:
            logger.error(f"Error generating test code: {str(e)}")
            raise
    
    def _identify_fixtures(self, test_case: TestCase, requirements: RequirementsAnalysis) -> list:
        """Identify required fixtures"""
        fixtures = ["browser", "logger"]  # Default fixtures
        
        scenario_lower = test_case.test_scenario.lower()
        
        if "login" in scenario_lower or "auth" in scenario_lower:
            fixtures.append("authenticated_session")
        if "database" in scenario_lower:
            fixtures.append("db_connection")
        if "api" in scenario_lower:
            fixtures.append("api_client")
        
        return fixtures
