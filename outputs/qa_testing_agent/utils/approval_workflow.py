"""
Approval Workflow Manager
Manages manual approval of generated test cases before execution
"""
import logging
import os
import json
from datetime import datetime
from typing import List, Tuple, Optional
from models import TestCase

logger = logging.getLogger(__name__)

class ApprovalStatus:
    """Approval status constants"""
    PENDING = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_REVISION = "NEEDS_REVISION"

class ApprovalWorkflow:
    """
    Manages manual approval workflow for generated test cases
    
    Flow:
    1. Generate test cases from stories -> Excel
    2. User reviews Excel file
    3. User approves, rejects, or requests revisions
    4. If approved -> continue with normal pipeline
    5. If rejected/revisions -> regenerate or manual fix
    """
    
    def __init__(self, excel_path: str, output_folder: str = "./approval_logs"):
        """
        Initialize approval workflow
        
        Args:
            excel_path: Path to generated Excel file
            output_folder: Folder for approval logs
        """
        self.excel_path = excel_path
        self.output_folder = output_folder
        self.approval_log = None
        os.makedirs(output_folder, exist_ok=True)
    
    def start_approval_workflow(self, 
                               test_cases: List[TestCase],
                               story_count: int = 0) -> Tuple[bool, str]:
        """
        Start manual approval workflow
        
        Args:
            test_cases: List of generated test cases
            story_count: Number of stories processed
            
        Returns:
            Tuple of (approved: bool, message: str)
        """
        logger.info("\n" + "="*70)
        logger.info("MANUAL TEST CASE APPROVAL WORKFLOW")
        logger.info("="*70)
        
        # Create approval summary
        summary = self._create_approval_summary(test_cases, story_count)
        
        # Display information
        self._display_approval_info(summary)
        
        # Save approval log
        self._save_approval_log(summary)
        
        # Get user decision
        decision = self._get_user_decision()
        
        if decision == "1":
            # Approved - continue
            logger.info("\nTest cases APPROVED - continuing with execution...")
            return True, "APPROVED"
            
        elif decision == "2":
            # Review Excel manually
            logger.info("\nPlease review and modify the Excel file:")
            logger.info(f"Location: {self.excel_path}")
            logger.info("\nMake your changes, then run the system again.")
            logger.info("The system will detect the modified file and continue.")
            return False, "MANUAL_REVIEW_REQUESTED"
            
        elif decision == "3":
            # Rejected - need regeneration
            logger.info("\nTest cases REJECTED")
            reason = input("\nProvide rejection reason (for logging): ").strip()
            self._log_rejection(reason)
            return False, f"REJECTED: {reason}"
            
        elif decision == "4":
            # Request revisions
            logger.info("\nRevision requested.")
            revisions = input("Describe required revisions: ").strip()
            self._log_revision_request(revisions)
            return False, f"REVISIONS_REQUESTED: {revisions}"
            
        else:
            logger.info("\nInvalid choice. Please try again.")
            return False, "INVALID_CHOICE"
    
    def _create_approval_summary(self, 
                                test_cases: List[TestCase], 
                                story_count: int) -> dict:
        """Create approval summary from test cases"""
        scenarios = {}
        total_steps = 0
        
        for test_case in test_cases:
            scenario = test_case.test_scenario
            if scenario not in scenarios:
                scenarios[scenario] = {
                    "test_cases": [],
                    "step_count": 0
                }
            
            scenarios[scenario]["test_cases"].append({
                "name": test_case.test_case_name,
                "steps": len(test_case.steps)
            })
            scenarios[scenario]["step_count"] += len(test_case.steps)
            total_steps += len(test_case.steps)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "stories_processed": story_count,
            "total_test_cases": len(test_cases),
            "total_scenarios": len(scenarios),
            "total_steps": total_steps,
            "scenarios": scenarios,
            "excel_path": self.excel_path
        }
    
    def _display_approval_info(self, summary: dict):
        """Display information for user approval"""
        print("\n" + "="*70)
        print("TEST CASE GENERATION SUMMARY")
        print("="*70)
        
        print(f"\nGenerated From: {summary['stories_processed']} user stories")
        print(f"Total Test Cases: {summary['total_test_cases']}")
        print(f"Total Scenarios: {summary['total_scenarios']}")
        print(f"Total Test Steps: {summary['total_steps']}")
        
        print("\n" + "-"*70)
        print("SCENARIOS GENERATED:")
        print("-"*70)
        
        for scenario, data in summary['scenarios'].items():
            print(f"\n[Scenario] {scenario}")
            print(f"   Test Cases: {len(data['test_cases'])}")
            print(f"   Total Steps: {data['step_count']}")
            for test_case in data['test_cases']:
                print(f"   - {test_case['name']} ({test_case['steps']} steps)")
        
        print("\n" + "="*70)
        print("EXCEL FILE LOCATION:")
        print(f"{summary['excel_path']}")
        print("="*70)
        
        print("\nPLEASE REVIEW THE EXCEL FILE FOR:")
        print("   - All test scenarios from stories are covered")
        print("   - All acceptance criteria are tested")
        print("   - Test steps are clear and actionable")
        print("   - Expected results are properly defined")
        print("   - Test data is appropriate")
        print("   - No duplicate test cases")
        print("   - Edge cases and error scenarios included")
        
    def _get_user_decision(self) -> str:
        """Get user approval decision"""
        print("\n" + "="*70)
        print("APPROVAL DECISION")
        print("="*70)
        
        print("\n1. APPROVE - Test cases look good, continue with execution")
        print("2. REVIEW - I need to manually review/modify the Excel file")
        print("3. REJECT - Test cases need to be regenerated")
        print("4. REVISIONS - Request specific revisions from AI")
        
        while True:
            choice = input("\nSelect option (1-4): ").strip()
            if choice in ["1", "2", "3", "4"]:
                return choice
            print("Invalid choice. Please select 1, 2, 3, or 4.")
    
    def _save_approval_log(self, summary: dict):
        """Save approval log"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(
            self.output_folder, 
            f"approval_log_{timestamp}.json"
        )
        
        with open(log_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Approval log saved: {log_file}")
        self.approval_log = log_file
    
    def _log_rejection(self, reason: str):
        """Log rejection decision"""
        if not self.approval_log:
            return
        
        with open(self.approval_log, 'r') as f:
            data = json.load(f)
        
        data["approval_decision"] = "REJECTED"
        data["rejection_reason"] = reason
        data["decision_timestamp"] = datetime.now().isoformat()
        
        with open(self.approval_log, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Rejection logged: {reason}")
    
    def _log_revision_request(self, revisions: str):
        """Log revision request"""
        if not self.approval_log:
            return
        
        with open(self.approval_log, 'r') as f:
            data = json.load(f)
        
        data["approval_decision"] = "REVISIONS_REQUESTED"
        data["revision_request"] = revisions
        data["decision_timestamp"] = datetime.now().isoformat()
        
        with open(self.approval_log, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Revision request logged: {revisions}")
    
    @staticmethod
    def create_approval_checklist() -> str:
        """
        Create a checklist for manual review
        
        Returns:
            HTML/Markdown checklist
        """
        checklist = """
# TEST CASE APPROVAL CHECKLIST

## Coverage Analysis
- [ ] All user stories are covered
- [ ] All acceptance criteria have test cases
- [ ] No gaps in requirement coverage
- [ ] Acceptance criteria are clearly mapped to test steps

## Test Quality
- [ ] Test steps are clear and actionable
- [ ] Test steps are not ambiguous
- [ ] Expected results are well-defined
- [ ] Test data is realistic and appropriate
- [ ] No duplicate test cases
- [ ] Tests follow naming conventions

## Scenario Coverage
- [ ] Happy path scenarios included
- [ ] Edge case scenarios included
- [ ] Error/negative scenarios included
- [ ] Boundary condition tests included
- [ ] Performance scenarios (if applicable)
- [ ] Security scenarios (if applicable)

## Test Data
- [ ] Test data is valid and realistic
- [ ] Data covers all scenarios
- [ ] Sensitive data is handled appropriately
- [ ] Data setup/cleanup is documented

## Overall Quality
- [ ] Test cases are well-organized
- [ ] Test scenarios are logically grouped
- [ ] Test cases are independent
- [ ] Total number of tests is reasonable
- [ ] Tests are maintainable long-term

## Sign-Off
- [ ] Reviewed by QA
- [ ] Approved for execution
- [ ] No blocking issues found
- [ ] Ready for automated execution
"""
        return checklist

class ApprovalDecisionHandler:
    """Handle different approval decisions"""
    
    @staticmethod
    def handle_approval(decision: str, excel_path: str) -> bool:
        """
        Handle approval decision
        
        Args:
            decision: Approval decision (APPROVED, REJECTED, etc.)
            excel_path: Path to Excel file
            
        Returns:
            True if should continue with execution
        """
        if decision == "APPROVED":
            logger.info("Test cases approved - proceeding with execution")
            return True
        
        elif decision == "MANUAL_REVIEW_REQUESTED":
            logger.info("Manual review requested")
            logger.info(f"Please review and modify: {excel_path}")
            logger.info("Run the system again when ready")
            return False
        
        elif decision.startswith("REJECTED"):
            logger.error(f"Test cases rejected - {decision}")
            return False
        
        elif decision.startswith("REVISIONS_REQUESTED"):
            logger.info(f"Revisions requested - {decision}")
            logger.info("Test case generator will be invoked with feedback")
            return False
        
        else:
            logger.warning(f"Unknown decision: {decision}")
            return False
    
    @staticmethod
    def should_continue_execution(decision: str) -> bool:
        """Check if should continue with execution"""
        return decision == "APPROVED"

class ManualApprovalHelper:
    """Helper utilities for manual approval workflow"""
    
    @staticmethod
    def open_excel_file(excel_path: str) -> bool:
        """
        Open Excel file for manual review
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            True if file was opened
        """
        try:
            import subprocess
            import platform
            
            system = platform.system()
            
            if system == "Windows":
                os.startfile(excel_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", excel_path])
            elif system == "Linux":
                subprocess.run(["xdg-open", excel_path])
            
            logger.info(f"Opened Excel file: {excel_path}")
            return True
            
        except Exception as e:
            logger.error(f"Could not open Excel file: {str(e)}")
            logger.info(f"Please manually open: {excel_path}")
            return False
    
    @staticmethod
    def wait_for_user_decision(timeout_seconds: int = 0) -> str:
        """
        Wait for user to review and make decision
        
        Args:
            timeout_seconds: Timeout in seconds (0 = no timeout)
            
        Returns:
            User's decision
        """
        if timeout_seconds > 0:
            logger.info(f"Waiting {timeout_seconds}s for user review...")
        
        return input("\nPress Enter when review is complete: ").strip()
    
    @staticmethod
    def get_approval_feedback() -> str:
        """Get detailed feedback from user"""
        print("\n" + "="*70)
        print("APPROVAL FEEDBACK")
        print("="*70)
        print("\nProvide any additional comments or feedback:")
        print("(Press Enter twice when done)")
        
        lines = []
        while True:
            line = input()
            if line == "":
                if lines and lines[-1] == "":
                    break
            lines.append(line)
        
        feedback = "\n".join(lines[:-1])  # Remove last empty line
        return feedback
    
    @staticmethod
    def log_approval_decision(excel_path: str, decision: str, feedback: str = ""):
        """
        Log approval decision to file
        
        Args:
            excel_path: Path to Excel file
            decision: Approval decision
            feedback: User feedback
        """
        log_path = excel_path.replace(".xlsx", "_approval.json")
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "feedback": feedback,
            "excel_file": excel_path
        }
        
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Approval decision logged: {log_path}")
