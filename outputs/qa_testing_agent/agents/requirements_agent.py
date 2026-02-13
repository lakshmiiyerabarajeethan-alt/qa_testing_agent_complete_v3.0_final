"""
Requirements Analysis Agent
Analyzes test case requirements using OpenAI
"""
import json
import logging
import re
from typing import Optional
from openai import OpenAI
from models import TestCase, RequirementsAnalysis
from config.settings import settings

logger = logging.getLogger(__name__)

class RequirementsAnalysisAgent:
    """Analyzes test case requirements"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    def analyze(self, test_case: TestCase, retry_context: Optional[str] = None) -> RequirementsAnalysis:
        """
        Analyze test case requirements
        
        Args:
            test_case: TestCase to analyze
            retry_context: Context if this is a retry due to data issue
            
        Returns:
            RequirementsAnalysis object
        """
        prompt = self._build_prompt(test_case, retry_context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert QA analyst specializing in requirements analysis.
                        Your job is to deeply understand test requirements, identify all edge cases,
                        and determine what test data is needed. Always respond with valid JSON."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS
            )
            
            result_text = response.choices[0].message.content or ""
            result_json = self._safe_parse_json(result_text)
            if result_json is None:
                logger.error("Failed to parse JSON response: empty or invalid content")
                logger.error(f"Raw model response (first 500 chars): {result_text[:500]}")
                return self._fallback_analysis(test_case, "Invalid JSON response")
            
            analysis = RequirementsAnalysis(
                test_case_id=f"{test_case.test_scenario}_{test_case.test_case_name}",
                scenario_understanding=result_json.get("scenario_understanding", ""),
                identified_requirements=result_json.get("identified_requirements", []),
                test_data_needs=result_json.get("test_data_needs", {}),
                assumptions=result_json.get("assumptions", [])
            )
            
            logger.info(f"Requirements analysis completed for {analysis.test_case_id}")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return self._fallback_analysis(test_case, "JSON parse error")
        except Exception as e:
            logger.error(f"Error analyzing requirements: {str(e)}")
            raise
    
    def _build_prompt(self, test_case: TestCase, retry_context: Optional[str] = None) -> str:
        """Build the analysis prompt"""
        steps_text = "\n".join([
            f"Step {step.step_no}: {step.description}\n  Expected: {step.expected_results}"
            for step in test_case.steps
        ])
        
        base_prompt = f"""Analyze the following test case and provide detailed requirements analysis:

Test Scenario: {test_case.test_scenario}
Test Case Name: {test_case.test_case_name}
Test Steps:
{steps_text}

Remarks: {test_case.remarks or 'None'}

Please provide a JSON response with the following structure:
{{
  "scenario_understanding": "Clear explanation of what this test case is validating",
  "identified_requirements": [
    "List of all functional requirements this test must cover",
    "Include both positive and negative scenarios"
  ],
  "test_data_needs": {{
    "user_type": "e.g., admin, regular user",
    "pre_conditions": "What system state is needed before test runs",
    "data_fields": {{"field_name": "description"}},
    "environmental_dependencies": ["any external systems needed"]
  }},
  "assumptions": ["Assumption 1", "Assumption 2"]
}}
"""
        
        if retry_context:
            base_prompt += f"\n\nPREVIOUS FEEDBACK (Retry context):\n{retry_context}\n\nPlease adjust the analysis and test data based on this feedback."
        
        return base_prompt

    def _fallback_analysis(self, test_case: TestCase, reason: str) -> RequirementsAnalysis:
        """
        Provide a minimal, best-effort requirements analysis to keep the pipeline moving
        when LLM output is not valid JSON.
        """
        scenario_text = (
            f"Fallback analysis due to {reason}. "
            f"Validate scenario '{test_case.test_scenario}' for test case '{test_case.test_case_name}'."
        )
        identified = [
            f"Validate steps for scenario: {test_case.test_scenario}",
            "Cover expected results for each step",
            "Include basic negative and edge conditions where applicable"
        ]
        test_data_needs = {
            "pre_conditions": "Environment ready for scenario execution",
            "data_fields": {},
            "environmental_dependencies": []
        }
        assumptions = [
            "System under test is accessible",
            "Test data can be created or mocked if needed"
        ]
        return RequirementsAnalysis(
            test_case_id=f"{test_case.test_scenario}_{test_case.test_case_name}",
            scenario_understanding=scenario_text,
            identified_requirements=identified,
            test_data_needs=test_data_needs,
            assumptions=assumptions
        )

    def _safe_parse_json(self, text: str):
        """
        Attempt to parse JSON from model output.
        Accepts raw JSON or JSON wrapped in code fences/text.
        """
        if not text:
            return None

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON object from response
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        snippet = cleaned[start:end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None
