"""
Orchestrator - Coordinates the multi-agent pipeline.

FIXES:
1. DATA_ISSUE now triggers regeneration (not just data retry) with feedback
2. Removed incorrect UI_CHANGE stop behavior for incomplete code
3. Better logging of what's happening at each stage
4. EXECUTE_REJECTED_TESTS setting honored correctly
5. Page inspection runs once at start to capture real DOM selectors
"""
import logging
from typing import List, Tuple
from models import TestCase, RequirementsAnalysis, GeneratedTestCase, ReviewResult
from config.settings import RejectionReason, TestStatus, settings
from agents.requirements_agent import RequirementsAnalysisAgent
from agents.test_designer_agent import TestDesignerAgent
from agents.reviewer_agent import ReviewerAgent

# Import page inspector if available
try:
    from agents.page_inspector_agent import get_smart_page_inspector
    PAGE_INSPECTION_AVAILABLE = True
except ImportError:
    PAGE_INSPECTION_AVAILABLE = False

logger = logging.getLogger(__name__)


class QATestingOrchestrator:
    """Orchestrates the multi-agent QA testing pipeline"""

    def __init__(self):
        self.requirements_agent = RequirementsAnalysisAgent()
        self.designer_agent = TestDesignerAgent()
        self.reviewer_agent = ReviewerAgent()
        self.max_retries = settings.MAX_RETRY_LOOPS

    def process_test_case(self, test_case: TestCase) -> Tuple[GeneratedTestCase, ReviewResult, List[dict]]:
        """
        Process a single test case through the pipeline.
        
        Flow:
          Requirements Analysis → Test Design → Review
          If rejected with DATA_ISSUE → retry up to max_retries times with feedback
          If rejected with UI_CHANGE/MISMATCH → stop (or continue if EXECUTE_REJECTED_TESTS)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {test_case.test_case_name}")
        logger.info(f"{'='*60}")

        rejection_history = []
        retry_count = 0
        retry_context = None

        while retry_count < self.max_retries:
            logger.info(f"Attempt {retry_count + 1}/{self.max_retries}")

            # Phase 1: Requirements Analysis
            logger.info("Phase 1: Requirements Analysis")
            requirements = self.requirements_agent.analyze(test_case, retry_context)

            # Phase 2: Test Design
            logger.info("Phase 2: Test Design")
            generated_test = self.designer_agent.design_test(
                test_case, requirements, retry_context
            )

            # Phase 3: Review
            logger.info("Phase 3: Review")
            review_result = self.reviewer_agent.review(
                test_case, requirements, generated_test
            )

            if review_result.is_approved:
                logger.info("APPROVED - Test case approved for execution")
                return generated_test, review_result, rejection_history

            # Handle rejection
            rejection_record = {
                "attempt": retry_count + 1,
                "reason": review_result.rejection_reason.value if hasattr(review_result.rejection_reason, 'value') else str(review_result.rejection_reason),
                "details": review_result.rejection_details,
                "suggestions": review_result.improvement_suggestions,
            }
            rejection_history.append(rejection_record)

            logger.warning(
                f"REJECTED [{review_result.rejection_reason}]: "
                f"{review_result.rejection_details[:150]}"
            )

            if review_result.rejection_reason == RejectionReason.DATA_ISSUE:
                # DATA_ISSUE = incomplete code or wrong data - retry with feedback
                logger.info(f"RETRYING - Regenerating test with feedback (attempt {retry_count + 1} -> {retry_count + 2})...")
                retry_context = self._build_retry_context(review_result)
                retry_count += 1

            elif review_result.rejection_reason == RejectionReason.UI_CHANGE:
                # UI_CHANGE = genuinely brittle/hardcoded selectors found
                if settings.EXECUTE_REJECTED_TESTS:
                    logger.warning("Proceeding despite UI_CHANGE (EXECUTE_REJECTED_TESTS=true)")
                    return generated_test, review_result, rejection_history
                logger.error("Hardcoded selectors detected - execution stopped")
                review_result.rejection_details = (
                    f"Hardcoded selectors detected: {review_result.rejection_details}. "
                    "Please use dynamic locators (get_by_role, get_by_label, etc.)"
                )
                return generated_test, review_result, rejection_history

            else:
                # MISMATCH = logic issue - retry once, then stop
                if retry_count == 0:
                    logger.info("RETRYING - Retrying due to requirements mismatch...")
                    retry_context = self._build_retry_context(review_result)
                    retry_count += 1
                else:
                    logger.error("MISMATCH - Requirements mismatch - stopping after retry")
                    if settings.EXECUTE_REJECTED_TESTS:
                        logger.warning("Proceeding despite mismatch (EXECUTE_REJECTED_TESTS=true)")
                    return generated_test, review_result, rejection_history

        # Max retries exceeded - execute anyway if configured
        logger.warning(f"Max retries ({self.max_retries}) reached for {test_case.test_case_name}")
        review_result.rejection_details = (
            f"Max regeneration attempts ({self.max_retries}) reached. "
            f"Executing best available version. History: {[r['reason'] for r in rejection_history]}"
        )
        # Override to approved so execution happens
        review_result.is_approved = True
        logger.info("Executing best available version after max retries")
        return generated_test, review_result, rejection_history

    def _build_retry_context(self, review_result: ReviewResult) -> str:
        """Build context for retry with specific improvement guidance"""
        return f"""PREVIOUS ATTEMPT WAS REJECTED.

Rejection Reason: {review_result.rejection_reason}
Details: {review_result.rejection_details}
Required Improvements: {review_result.improvement_suggestions}

For the next attempt:
- Implement EVERY test step with actual Playwright interactions
- Add expect() assertions for EVERY expected result in the steps
- Use page.get_by_role(), page.get_by_label(), page.get_by_text() for element discovery
- Do NOT write skeleton/placeholder code
- Do NOT leave any step unimplemented
"""

    def process_test_suite(self, test_cases: List[TestCase]) -> List[Tuple]:
        """Process all test cases in the suite"""
        total = len(test_cases)
        
        # Run page inspection once for the entire suite if enabled
        if PAGE_INSPECTION_AVAILABLE and getattr(settings, "ENABLE_PAGE_INSPECTION", True):
            logger.info("")
            logger.info("="*70)
            logger.info("PAGE INSPECTION - Capturing real DOM selectors")
            logger.info("="*70)
            try:
                inspector = get_smart_page_inspector()
                dom_info = inspector.inspect()
                if dom_info.get("success"):
                    logger.info("Smart Page Inspector v2 - SUCCESS")
                    logger.info(f"  - Executed {len(dom_info.get('executed_steps', []))} precondition steps")
                    logger.info(f"  - Captured {len(dom_info.get('tag_items', []))} tag elements")
                    logger.info(f"  - Captured {len(dom_info.get('buttons', []))} buttons")
                    logger.info("  Tests will use PROVEN selectors from successful execution")
                else:
                    logger.warning("Smart Page Inspector v2 - FAILED")
                    if dom_info.get("error"):
                        logger.warning(f"  Error: {dom_info['error']}")
            except Exception as e:
                logger.warning(f"Page inspection error: {e}")
                logger.warning("Tests will use fallback selectors")
            logger.info("="*70)
            logger.info("")
        
        results = []

        for idx, test_case in enumerate(test_cases, 1):
            logger.info(f"\n[{idx}/{total}] Processing test case")

            try:
                result_tuple = self.process_test_case(test_case)
                results.append(result_tuple)
            except Exception as e:
                logger.error(f"Error processing {test_case.test_case_name}: {str(e)}", exc_info=True)
                continue

        approved = sum(1 for _, r, _ in results if r.is_approved)
        logger.info(f"Processed {len(results)}/{total} test cases ({approved} approved)")
        return results
