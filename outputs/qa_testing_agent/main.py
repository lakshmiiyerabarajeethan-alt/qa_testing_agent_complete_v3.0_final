"""
Main entry point for QA Testing Agent
Supports both Azure DevOps stories and manual Excel test cases
"""
import logging
import sys
import os
from datetime import datetime
from typing import Optional

from config.settings import settings
from parsers.excel_parser import TestCaseParser
from orchestrator import QATestingOrchestrator
from executors.test_executor import TestExecutor
from utils.report_generator import HTMLReportGenerator
from utils.excel_writer import ExcelWriter
from utils.test_case_reviewer import TestCaseReviewer, QuickApprovalMode

# Import CSV story reader and test case generator
try:
    from connectors.csv_story_reader import CSVStoryReader
    from agents.test_case_generator_agent import TestCaseGeneratorAgent
    CSV_STORIES_AVAILABLE = True
except ImportError:
    CSV_STORIES_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qa_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class QATestingPipeline:
    """Main pipeline orchestrator with Azure DevOps support"""
    
    def __init__(self):
        self.parser = TestCaseParser(settings.TEST_INPUT_FOLDER)
        self.orchestrator = QATestingOrchestrator()
        self.executor = TestExecutor(settings.REPORT_OUTPUT_FOLDER)
        self.report_generator = HTMLReportGenerator(settings.REPORT_OUTPUT_FOLDER)
        self.excel_writer = ExcelWriter(settings.TEST_INPUT_FOLDER)
    
    def run_from_csv_stories(self, stories_folder: str = "./stories") -> str:
        """Run pipeline with test cases generated from CSV stories"""
        if not CSV_STORIES_AVAILABLE:
            logger.error("CSV story reader not available")
            return ""
        
        logger.info("="*70)
        logger.info("QA TESTING AGENT - CSV STORIES INTEGRATION")
        logger.info("="*70)
        
        pipeline_start = datetime.now()
        
        # Phase 1: Read CSV stories
        logger.info("\n[Phase 1] Reading stories from CSV files...")
        reader = CSVStoryReader(stories_folder)
        
        # List available CSV files
        csv_files = reader.list_csv_files()
        if csv_files:
            logger.info(f"Found CSV files: {', '.join(csv_files)}")
        
        stories = reader.read_all_stories()
        if not stories:
            logger.error(f"No stories found in {stories_folder}")
            logger.info(f"Place CSV files in: {os.path.abspath(stories_folder)}")
            return ""
        
        logger.info(f"Loaded {len(stories)} user stories from CSV")
        
        # Phase 3: Generate test cases
        logger.info("\n[Phase 3] Generating test cases from stories...")
        generator = TestCaseGeneratorAgent()
        test_cases = generator.generate_test_cases_from_stories(stories)
        
        if not test_cases:
            logger.error("No test cases generated!")
            return ""
        
        logger.info(f"Generated {len(test_cases)} test cases")
        
        # Phase 4: Save to Excel
        logger.info("\n[Phase 4] Saving test cases to Excel...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = self.excel_writer.write_test_cases(
            test_cases, f"devops_tests_{timestamp}.xlsx"
        )
        
        # Phase 5: MANUAL APPROVAL (NEW)
        logger.info("\n[Phase 5] Manual test case approval workflow...")
        from utils.approval_workflow import ApprovalWorkflow, ApprovalDecisionHandler
        
        workflow = ApprovalWorkflow(excel_path)
        approved, decision = workflow.start_approval_workflow(test_cases, len(stories))
        
        if not approved:
            logger.info(f"\n⏸️  Workflow paused for: {decision}")
            logger.info("\nNext steps:")
            
            if decision == "MANUAL_REVIEW_REQUESTED":
                logger.info("1. Review and modify the Excel file")
                logger.info("2. Run the system again to continue")
                logger.info(f"   File: {excel_path}")
            elif "REJECTED" in decision:
                logger.info("Test cases rejected. Options:")
                logger.info("1. Modify the Excel file manually and run again")
                logger.info("2. Run Azure DevOps integration again with feedback")
            elif "REVISIONS" in decision:
                logger.info("Revisions requested. Please modify the Excel file.")
                logger.info("Run the system again when ready.")
            
            return ""
        
        # Phase 6+: Continue with normal pipeline (test cases approved)
        logger.info("\n[Phase 6] Running analysis and design pipeline...")
        test_results = self.orchestrator.process_test_suite(test_cases)
        
        if not test_results:
            return ""
        
        approved_tests = [
            gen_test for gen_test, review, _ in test_results 
            if review.is_approved
        ]
        
        logger.info(f"{len(approved_tests)}/{len(test_results)} tests approved for execution")
        
        logger.info("\n[Phase 7] Executing approved tests...")
        execution_results = []
        if approved_tests:
            execution_results = self.executor.execute_batch(approved_tests)
        
        logger.info("\n[Phase 8] Generating final report...")
        suite_id = f"devops_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_path = self.report_generator.generate_report(
            test_results, execution_results, suite_id
        )
        
        self._print_summary(test_results, execution_results, pipeline_start,
                           len(stories), excel_path)
        
        return report_path
    
    def run_from_excel(self) -> str:
        """Run pipeline with test cases from Excel files"""
        logger.info("="*70)
        logger.info("QA TESTING AGENT - EXCEL INPUT")
        logger.info("="*70)
        
        pipeline_start = datetime.now()
        
        logger.info("\n[Phase 1] Parsing test cases from Excel...")
        test_cases = self.parser.parse_folder()
        
        if not test_cases:
            logger.error("No test cases found!")
            return ""
        
        logger.info(f"Parsed {len(test_cases)} test cases")
        
        logger.info("\n[Phase 2] Running multi-agent pipeline...")
        test_results = self.orchestrator.process_test_suite(test_cases)
        
        if not test_results:
            return ""
        
        approved_tests = [
            gen_test for gen_test, review, _ in test_results 
            if review.is_approved
        ]
        
        logger.info(f"{len(approved_tests)}/{len(test_results)} tests approved")
        
        logger.info("\n[Phase 3] Executing approved tests...")
        execution_results = []
        if approved_tests:
            execution_results = self.executor.execute_batch(approved_tests)
        
        logger.info("\n[Phase 4] Generating report...")
        suite_id = f"qa_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_path = self.report_generator.generate_report(
            test_results, execution_results, suite_id
        )
        
        self._print_summary(test_results, execution_results, pipeline_start)
        return report_path
    
    def _print_summary(self, test_results, execution_results, start_time, 
                      story_count: int = 0, excel_path: str = ""):
        """Print execution summary"""
        total = len(test_results)
        approved = sum(1 for _, r, _ in test_results if r.is_approved)
        rejected = total - approved
        
        passed = sum(1 for r in execution_results if r.status.value == "PASSED")
        failed = sum(1 for r in execution_results if r.status.value == "FAILED")
        
        duration = (datetime.now() - start_time).total_seconds()
        rate = (passed / len(execution_results) * 100) if execution_results else 0
        
        logger.info("\n" + "="*70)
        logger.info("EXECUTION SUMMARY")
        logger.info("="*70)
        
        if story_count > 0:
            logger.info(f"Stories Processed: {story_count}")
            logger.info(f"Excel Generated: {excel_path}")
        
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Total Tests: {total} (Approved: {approved}, Rejected: {rejected})")
        
        if execution_results:
            logger.info(f"Results: Passed: {passed}, Failed: {failed}, Rate: {rate:.1f}%")
        
        logger.info("="*70 + "\n")

def main():
    """Main entry point"""
    try:
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY not set!")
            return 1
        
        os.makedirs(settings.TEST_INPUT_FOLDER, exist_ok=True)
        os.makedirs(settings.REPORT_OUTPUT_FOLDER, exist_ok=True)
        
        # Interactive mode
        print("\n" + "="*70)
        print("QA TESTING AGENT")
        print("="*70)
        
        if CSV_STORIES_AVAILABLE:
            print("\n1. CSV Stories (import from any system)")
            print("2. Excel Files (manual test cases)")
            print("3. Create Sample CSV")
            print("4. Create Excel Template")
            choice = input("\nSelect option (1-4): ").strip()
        else:
            print("\nRunning with Excel files...")
            choice = "2"
        
        pipeline = QATestingPipeline()
        report_path = ""
        
        if choice == "1" and CSV_STORIES_AVAILABLE:
            print("\n" + "="*70)
            print("CSV STORIES CONFIGURATION")
            print("="*70)
            folder = input("Stories folder (default: ./stories): ").strip()
            if not folder:
                folder = "./stories"
            
            report_path = pipeline.run_from_csv_stories(stories_folder=folder)
        elif choice == "2":
            report_path = pipeline.run_from_excel()
        elif choice == "3":
            # Create sample CSV
            reader = CSVStoryReader()
            sample_path = reader.create_sample_csv()
            logger.info(f"\nSample CSV created: {sample_path}")
            logger.info("Please add your own CSV files to the stories folder")
            return 0
        elif choice == "4":
            # Create Excel template
            writer = ExcelWriter(settings.TEST_INPUT_FOLDER)
            template = writer.create_template()
            logger.info(f"Template created: {template}")
            return 0
        
        if report_path:
            logger.info(f"\nReport: {report_path}")
            return 0
        else:
            logger.error("\nPipeline failed")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
