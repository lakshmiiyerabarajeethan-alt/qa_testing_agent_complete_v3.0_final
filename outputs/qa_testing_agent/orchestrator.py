"""
Orchestrator for multi-agent QA testing workflow
Coordinates Requirements -> Test Designer -> Reviewer -> Executor
"""
import logging
from typing import List, Tuple, Optional
from models import (TestCase, RequirementsAnalysis, GeneratedTestCase, 
                    ReviewResult, TestSuiteResult, TestExecutionResult)
from config.settings import RejectionReason, TestStatus, settings
from agents.requirements_agent import RequirementsAnalysisAgent
from agents.test_designer_agent import TestDesignerAgent
from agents.reviewer_agent import ReviewerAgent

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
        Process a single test case through the pipeline
        
        Args:
            test_case: Test case to process
            
        Returns:
            Tuple of (GeneratedTestCase, ReviewResult, rejection_history)
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
                logger.info("Test case APPROVED")
                return generated_test, review_result, rejection_history
            
            # Handle rejection
            rejection_record = {
                "attempt": retry_count + 1,
                "reason": review_result.rejection_reason,
                "details": review_result.rejection_details,
                "suggestions": review_result.improvement_suggestions
            }
            rejection_history.append(rejection_record)
            
            logger.warning(
                f"Test case REJECTED: {review_result.rejection_reason} - "
                f"{review_result.rejection_details}"
            )
            
            # Check rejection type and decide on retry
            if review_result.rejection_reason == RejectionReason.DATA_ISSUE:
                # Auto-retry with modified data
                logger.info("Retrying with adjusted requirements and data...")
                retry_context = self._build_retry_context(review_result)
                retry_count += 1
                
            elif review_result.rejection_reason == RejectionReason.UI_CHANGE:
                # Stop execution - UI changed
                if settings.EXECUTE_REJECTED_TESTS:
                    logger.warning("UI change detected - continuing due to EXECUTE_REJECTED_TESTS")
                    return generated_test, review_result, rejection_history
                logger.error("UI change detected - stopping execution")
                review_result.rejection_details = (
                    f"UI change detected: {review_result.rejection_details}. "
                    "Execution stopped. Please update test case manually."
                )
                return generated_test, review_result, rejection_history
                
            else:
                # Requirement mismatch - stop and report
                logger.error("Requirement mismatch - stopping execution")
                return generated_test, review_result, rejection_history
        
        # Max retries exceeded
        logger.error(f"Max retries ({self.max_retries}) exceeded")
        review_result.rejection_details = (
            f"Max retries ({self.max_retries}) exceeded. "
            f"Rejection history: {rejection_history}"
        )
        return generated_test, review_result, rejection_history
    
    def _build_retry_context(self, review_result: ReviewResult) -> str:
        """Build context for retry based on rejection"""
        context = f"""Previous attempt was rejected due to: {review_result.rejection_reason}

Details: {review_result.rejection_details}

Suggestions for improvement: {review_result.improvement_suggestions}

Please adjust the requirements and test data accordingly for the next attempt."""
        
        return context
    
    def process_test_suite(self, test_cases: List[TestCase]) -> List[Tuple]:
        """
        Process entire test suite
        
        Args:
            test_cases: List of test cases to process
            
        Returns:
            List of (GeneratedTestCase, ReviewResult, rejection_history) tuples
        """
        results = []
        
        for idx, test_case in enumerate(test_cases, 1):
            logger.info(f"\n[{idx}/{len(test_cases)}] Processing test case")
            
            try:
                generated_test, review_result, rejection_history = self.process_test_case(
                    test_case
                )
                results.append((generated_test, review_result, rejection_history))
                
            except Exception as e:
                logger.error(f"Error processing test case: {str(e)}", exc_info=True)
                # Continue with next test case
                continue
        
        logger.info(f"\nProcessed {len(results)} test cases")
        return results
