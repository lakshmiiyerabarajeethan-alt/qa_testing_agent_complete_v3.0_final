"""
Reviewer Agent
Reviews generated tests for quality and correctness
"""
import json
import logging
from typing import Optional
from openai import OpenAI
from models import (TestCase, RequirementsAnalysis, GeneratedTestCase, 
                    ReviewResult)
from config.settings import settings, RejectionReason

logger = logging.getLogger(__name__)

class ReviewerAgent:
    """Reviews generated test cases"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    def review(self, 
               test_case: TestCase,
               requirements: RequirementsAnalysis,
               generated_test: GeneratedTestCase) -> ReviewResult:
        """
        Review the generated test case
        
        Args:
            test_case: Original test case
            requirements: Requirements analysis
            generated_test: Generated test code and data
            
        Returns:
            ReviewResult with approval status and feedback
        """
        review_feedback = self._get_review_from_llm(
            test_case, requirements, generated_test
        )
        
        result = ReviewResult(
            test_case_id=generated_test.test_case_id,
            is_approved=review_feedback.get("is_approved", False),
            rejection_reason=self._parse_rejection_reason(
                review_feedback.get("rejection_reason")
            ),
            rejection_details=review_feedback.get("rejection_details"),
            improvement_suggestions=review_feedback.get("improvement_suggestions")
        )
        
        logger.info(
            f"Review completed for {result.test_case_id}: "
            f"{'APPROVED' if result.is_approved else 'REJECTED'}"
        )
        return result
    
    def _get_review_from_llm(self,
                            test_case: TestCase,
                            requirements: RequirementsAnalysis,
                            generated_test: GeneratedTestCase) -> dict:
        """Get review feedback from LLM"""
        steps_text = "\n".join([
            f"Step {step.step_no}: {step.description} => {step.expected_results}"
            for step in test_case.steps
        ])
        
        prompt = f"""You are an expert QA reviewer. Review this generated test case for quality, correctness, and alignment with requirements.

Test Case: {test_case.test_case_name}
Scenario: {test_case.test_scenario}

Requirements:
{requirements.scenario_understanding}

Test Steps:
{steps_text}

Generated Test Code:
{generated_test.test_code[:500]}...

Test Data:
{json.dumps(generated_test.test_data, indent=2)}

Review the following aspects:
1. Does the test code correctly implement all steps?
2. Are assertions aligned with expected results?
3. Is the test data appropriate and realistic?
4. Are there any potential flakiness issues?
5. Is error handling adequate?
6. Does it follow best practices?

Return a JSON response with:
{{
  "is_approved": true/false,
  "rejection_reason": "NONE|DATA_ISSUE|UI_CHANGE|REQUIREMENT_MISMATCH",
  "rejection_details": "Explanation if rejected",
  "improvement_suggestions": "Suggestions for improvement"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a senior QA reviewer with extensive experience in UI automation testing.
                        Be thorough but fair in your reviews. Always return valid JSON."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temp for consistency
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)
            
            return result_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review JSON: {str(e)}")
            return {
                "is_approved": False,
                "rejection_reason": "REQUIREMENT_MISMATCH",
                "rejection_details": f"Failed to parse review: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error during review: {str(e)}")
            raise
    
    def _parse_rejection_reason(self, reason_str: Optional[str]) -> RejectionReason:
        """Parse rejection reason from string"""
        if not reason_str:
            return RejectionReason.NONE
        
        reason_str = reason_str.upper()
        
        if "DATA" in reason_str:
            return RejectionReason.DATA_ISSUE
        elif "UI" in reason_str:
            return RejectionReason.UI_CHANGE
        elif "REQUIREMENT" in reason_str:
            return RejectionReason.REQUIREMENT_MISMATCH
        else:
            return RejectionReason.NONE
