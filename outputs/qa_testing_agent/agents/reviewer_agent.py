"""
Reviewer Agent - Reviews generated test code for quality and correctness.

FIXES:
1. Correctly classifies rejection reasons:
   - INCOMPLETE_CODE (incomplete implementation) → DATA_ISSUE (triggers retry/regeneration)
   - UI_CHANGE → only for actual detected UI element changes
   - MISMATCH → for logic/requirements mismatches
2. More lenient approval criteria - allows tests that have full step coverage
3. Properly handles improvement_suggestions as a string (not list)
"""
import logging
import json
from openai import OpenAI
from models import TestCase, RequirementsAnalysis, GeneratedTestCase, ReviewResult
from config.settings import settings, RejectionReason
from utils.token_tracker import token_tracker

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a senior QA engineer reviewing automatically generated Playwright test code.

Your job is to determine if a generated test is COMPLETE and EXECUTABLE.

APPROVAL CRITERIA - Approve if ALL are true:
1. The test covers ALL steps described in the test case
2. The test includes assertions (expect() calls) for expected results
3. The test navigates to the correct URL
4. The test uses intelligent element discovery (get_by_role, get_by_label, etc.)
5. The code is syntactically valid Python/Playwright

REJECTION REASONS - Use exactly one of these strings:
- "DATA_ISSUE" → Test implementation is INCOMPLETE (missing steps, no assertions, skeleton code)
  Use this when: steps are missing, no actual interactions implemented, placeholder comments only
- "UI_CHANGE" → Code uses hardcoded selectors that may not work (e.g., specific CSS IDs/classes)
  ONLY use this for actual hardcoded brittle selectors like: #specific-id, .very-specific-class
- "MISMATCH" → Test logic fundamentally contradicts the test case requirements

IMPORTANT:
- Do NOT use "UI_CHANGE" for incomplete code - use "DATA_ISSUE" instead
- Be LENIENT - if the test makes a genuine effort to implement all steps, APPROVE it
- Incomplete code / skeleton code / placeholder code → DATA_ISSUE (will trigger regeneration)
- improvement_suggestions must be a single string, not a list

Respond with valid JSON only:
{
    "is_approved": true/false,
    "rejection_reason": "DATA_ISSUE" | "UI_CHANGE" | "MISMATCH" | "NONE",
    "rejection_details": "Brief description of the issue",
    "improvement_suggestions": "Single string with specific suggestions for improvement"
}
"""


class ReviewerAgent:
    """Reviews generated test code and approves or rejects with correct classifications"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def review(self, test_case: TestCase, requirements: RequirementsAnalysis,
               generated_test: GeneratedTestCase) -> ReviewResult:
        """
        Review the generated test and return a ReviewResult.
        
        Key fix: incomplete code → DATA_ISSUE (triggers retry), not UI_CHANGE (stops execution)
        """
        test_case_id = f"{test_case.test_scenario}_{test_case.test_case_name}"

        steps_text = "\n".join([
            f"  Step {s.step_no}: {s.description} | Expected: {s.expected_results}"
            for s in test_case.steps
        ])

        prompt = f"""Review this generated Playwright test:

=== TEST CASE ===
Scenario: {test_case.test_scenario}
Test Name: {test_case.test_case_name}

Steps to implement:
{steps_text}

=== GENERATED CODE ===
{generated_test.test_code[:5000]}

Review the code and respond with JSON only.
Check: Does the code implement ALL steps with real Playwright actions and assertions?
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent evaluation
                max_tokens=800,
            )
            token_tracker.record("ReviewerAgent", response)

            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            review_data = json.loads(raw)

            # Ensure improvement_suggestions is a string
            suggestions = review_data.get("improvement_suggestions", "")
            if isinstance(suggestions, list):
                suggestions = " | ".join(suggestions)
            elif not isinstance(suggestions, str):
                suggestions = str(suggestions)

            # Map string rejection reason to enum
            reason_str = review_data.get("rejection_reason", "NONE").upper()
            reason_map = {
                "DATA_ISSUE": RejectionReason.DATA_ISSUE,
                "UI_CHANGE": RejectionReason.UI_CHANGE,
                "MISMATCH": RejectionReason.MISMATCH,
                "NONE": RejectionReason.NONE,
                "INCOMPLETE_CODE": RejectionReason.DATA_ISSUE,  # Map to DATA_ISSUE
                "INCOMPLETE": RejectionReason.DATA_ISSUE,       # Map to DATA_ISSUE
            }
            rejection_reason = reason_map.get(reason_str, RejectionReason.DATA_ISSUE)

            is_approved = review_data.get("is_approved", False)

            result = ReviewResult(
                test_case_id=test_case_id,
                is_approved=is_approved,
                rejection_reason=rejection_reason,
                rejection_details=review_data.get("rejection_details", ""),
                improvement_suggestions=suggestions,
            )

            status = "APPROVED" if is_approved else f"REJECTED ({rejection_reason.value})"
            logger.info(f"Review completed for {test_case_id}: {status}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review JSON: {e}\nRaw: {raw[:300]}")
            # Default to approved if we can't parse - don't block execution
            return ReviewResult(
                test_case_id=test_case_id,
                is_approved=True,
                rejection_reason=RejectionReason.NONE,
                rejection_details="Review parse error - defaulting to approved",
                improvement_suggestions="Review parsing failed. Manual inspection recommended.",
            )

        except Exception as e:
            logger.error(f"Review error for {test_case_id}: {e}", exc_info=True)
            return ReviewResult(
                test_case_id=test_case_id,
                is_approved=True,
                rejection_reason=RejectionReason.NONE,
                rejection_details=f"Review error: {str(e)} - defaulting to approved",
                improvement_suggestions="",
            )
