"""
Requirements Analysis Agent - Analyzes test case steps and extracts
structured requirements for the Test Designer Agent.

Updated to pass BASE_URL and credentials as part of analysis so the designer
has all the context it needs to generate complete tests.
"""
import logging
import json
from openai import OpenAI
from models import TestCase, RequirementsAnalysis
from config.settings import settings
from utils.token_tracker import token_tracker

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a senior QA engineer analyzing test cases.

Extract structured requirements from the test case steps.
Focus on:
1. What the test scenario is testing
2. What actions need to be performed (clicks, form fills, navigation, etc.)
3. What assertions need to be made (verifications, checks)
4. What data is needed

Return valid JSON only:
{
    "scenario_understanding": "Clear description of what this test verifies",
    "identified_requirements": ["requirement 1", "requirement 2", ...],
    "test_data_needs": {
        "key": "value describing what data is needed"
    },
    "assumptions": ["assumption 1", "assumption 2"]
}
"""


class RequirementsAnalysisAgent:
    """Analyzes test case requirements for the test designer"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def analyze(self, test_case: TestCase, retry_context: str = None) -> RequirementsAnalysis:
        """Analyze test case and extract requirements"""

        steps_text = "\n".join([
            f"  Step {s.step_no}: {s.description}\n  Expected: {s.expected_results}"
            for s in test_case.steps
        ])

        prompt = f"""Analyze this test case and extract requirements:

Test Scenario: {test_case.test_scenario}
Test Case: {test_case.test_case_name}
Base URL: {settings.BASE_URL}

Steps:
{steps_text}

Additional Test Data: {json.dumps(test_case.test_data or {}, indent=2)}

Return JSON with requirements analysis.
"""

        if retry_context:
            prompt = f"Previous attempt context:\n{retry_context}\n\n{prompt}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            token_tracker.record("RequirementsAgent", response)

            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(raw)

            test_case_id = f"{test_case.test_scenario}_{test_case.test_case_name}"

            result = RequirementsAnalysis(
                test_case_id=test_case_id,
                scenario_understanding=data.get("scenario_understanding", ""),
                identified_requirements=data.get("identified_requirements", []),
                test_data_needs=data.get("test_data_needs", {}),
                assumptions=data.get("assumptions", []),
            )

            logger.info(f"Requirements analysis completed for {test_case_id}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse requirements JSON: {e}")
            test_case_id = f"{test_case.test_scenario}_{test_case.test_case_name}"
            return RequirementsAnalysis(
                test_case_id=test_case_id,
                scenario_understanding=f"Test case: {test_case.test_scenario} - {test_case.test_case_name}",
                identified_requirements=[s.description for s in test_case.steps],
                test_data_needs={"base_url": settings.BASE_URL},
                assumptions=["Standard browser-based web application"],
            )

        except Exception as e:
            logger.error(f"Requirements analysis error: {e}", exc_info=True)
            test_case_id = f"{test_case.test_scenario}_{test_case.test_case_name}"
            return RequirementsAnalysis(
                test_case_id=test_case_id,
                scenario_understanding=test_case.test_scenario,
                identified_requirements=[s.description for s in test_case.steps],
                test_data_needs={},
                assumptions=[],
            )
