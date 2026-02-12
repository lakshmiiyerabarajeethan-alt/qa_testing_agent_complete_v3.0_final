"""
Test Case Approval/Review Module
Provides interactive CLI interface for reviewing and approving generated test cases
"""
import logging
import json
import os
from typing import List, Tuple, Dict
from models import TestCase, TestStep
from config.settings import TestStatus

logger = logging.getLogger(__name__)

class TestCaseReviewer:
    """
    Interactive interface for reviewing and approving test cases
    Allows manual intervention before test execution
    """
    
    def __init__(self):
        self.approval_status = {}  # Track which test cases are approved
    
    def review_test_cases(self, test_cases: List[TestCase]) -> Tuple[List[TestCase], Dict]:
        """
        Interactive review of test cases
        
        Args:
            test_cases: List of TestCase objects to review
            
        Returns:
            Tuple of (approved_test_cases, approval_status_dict)
        """
        logger.info("\n" + "="*70)
        logger.info("MANUAL TEST CASE APPROVAL STEP")
        logger.info("="*70)
        logger.info(f"\nTotal test cases to review: {len(test_cases)}\n")
        
        approved_tests = []
        approval_status = {
            "total": len(test_cases),
            "approved": 0,
            "rejected": 0,
            "modified": 0,
            "details": []
        }
        
        for idx, test_case in enumerate(test_cases, 1):
            logger.info(f"\n[{idx}/{len(test_cases)}] Reviewing Test Case")
            logger.info("="*70)
            
            # Display test case details
            self._display_test_case(test_case, idx)
            
            # Get user approval
            while True:
                choice = input("\nApprove this test case? (y/n/m/s): ").strip().lower()
                
                if choice == 'y':
                    # Approved
                    approved_tests.append(test_case)
                    approval_status["approved"] += 1
                    approval_status["details"].append({
                        "test_case": test_case.test_case_name,
                        "scenario": test_case.test_scenario,
                        "status": "APPROVED",
                        "reason": None
                    })
                    logger.info("Test case APPROVED\n")
                    break
                    
                elif choice == 'n':
                    # Rejected
                    reason = input("Reason for rejection: ").strip()
                    approval_status["rejected"] += 1
                    approval_status["details"].append({
                        "test_case": test_case.test_case_name,
                        "scenario": test_case.test_scenario,
                        "status": "REJECTED",
                        "reason": reason
                    })
                    logger.info(f"Test case REJECTED: {reason}\n")
                    break
                    
                elif choice == 'm':
                    # Modify
                    modified_case = self._modify_test_case(test_case)
                    if modified_case:
                        approved_tests.append(modified_case)
                        approval_status["approved"] += 1
                        approval_status["modified"] += 1
                        approval_status["details"].append({
                            "test_case": modified_case.test_case_name,
                            "scenario": modified_case.test_scenario,
                            "status": "APPROVED_MODIFIED",
                            "reason": "Manually modified and approved"
                        })
                        logger.info("Test case MODIFIED and APPROVED\n")
                        break
                    
                elif choice == 's':
                    # Skip for now, return to this later
                    logger.info("⊙ Test case SKIPPED for now\n")
                    break
                    
                else:
                    print("Invalid choice. Use 'y' (approve), 'n' (reject), 'm' (modify), 's' (skip)")
        
        # Print summary
        self._print_approval_summary(approval_status)
        
        return approved_tests, approval_status
    
    def _display_test_case(self, test_case: TestCase, index: int) -> None:
        """Display test case details for review"""
        logger.info(f"Scenario: {test_case.test_scenario}")
        logger.info(f"Test Case: {test_case.test_case_name}")
        
        if test_case.remarks:
            logger.info(f"Remarks: {test_case.remarks}")
        
        if test_case.test_data:
            logger.info(f"Test Data: {test_case.test_data}")
        
        logger.info(f"\nSteps ({len(test_case.steps)}):")
        logger.info("-" * 70)
        
        for step in test_case.steps:
            logger.info(f"  Step {step.step_no}: {step.description}")
            logger.info(f"    Expected: {step.expected_results}")
        
        logger.info("-" * 70)
    
    def _modify_test_case(self, test_case: TestCase) -> TestCase:
        """
        Allow user to modify test case details
        
        Args:
            test_case: TestCase to modify
            
        Returns:
            Modified TestCase or None if user cancels
        """
        logger.info("\nMODIFY TEST CASE")
        logger.info("="*70)
        logger.info("What would you like to modify?")
        logger.info("1. Test case name")
        logger.info("2. Add/modify remarks")
        logger.info("3. Edit test steps")
        logger.info("4. Cancel modification")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            new_name = input("New test case name: ").strip()
            if new_name:
                test_case.test_case_name = new_name
                logger.info(f"Test case name updated to: {new_name}")
        
        elif choice == '2':
            new_remarks = input("New remarks: ").strip()
            if new_remarks:
                test_case.remarks = new_remarks
                logger.info("Remarks updated")
        
        elif choice == '3':
            logger.info("\nCurrent steps:")
            for step in test_case.steps:
                logger.info(f"  Step {step.step_no}: {step.description}")
            
            step_num = input("\nEnter step number to edit (or press Enter to skip): ").strip()
            if step_num.isdigit():
                step_num = int(step_num)
                for step in test_case.steps:
                    if step.step_no == step_num:
                        new_desc = input(f"New description for step {step_num}: ").strip()
                        if new_desc:
                            step.description = new_desc
                        new_expected = input(f"New expected result for step {step_num}: ").strip()
                        if new_expected:
                            step.expected_results = new_expected
                        logger.info(f"Step {step_num} updated")
                        break
        
        elif choice == '4':
            logger.info("Modification cancelled")
            return None
        
        return test_case
    
    def _print_approval_summary(self, approval_status: Dict) -> None:
        """Print approval summary"""
        logger.info("\n" + "="*70)
        logger.info("APPROVAL SUMMARY")
        logger.info("="*70)
        logger.info(f"Total test cases: {approval_status['total']}")
        logger.info(f"Approved: {approval_status['approved']}")
        logger.info(f"Rejected: {approval_status['rejected']}")
        logger.info(f"Modified: {approval_status['modified']}")
        
        if approval_status['rejected'] > 0:
            logger.info("\nRejected Test Cases:")
            for detail in approval_status['details']:
                if detail['status'] == 'REJECTED':
                    logger.info(f"  - {detail['test_case']}: {detail['reason']}")
        
        logger.info("="*70 + "\n")
    
    def save_approval_status(self, approval_status: Dict, filepath: str = "approval_status.json") -> str:
        """
        Save approval status to file for reference
        
        Args:
            approval_status: Approval status dictionary
            filepath: Path to save the file
            
        Returns:
            Path to saved file
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(approval_status, f, indent=2)
            logger.info(f"Approval status saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving approval status: {str(e)}")
            return ""
    
    def load_approval_status(self, filepath: str) -> Dict:
        """Load approval status from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading approval status: {str(e)}")
        
        return {}
    
    def create_approval_report(self, approval_status: Dict, output_path: str = "approval_report.txt") -> str:
        """
        Create a human-readable approval report
        
        Args:
            approval_status: Approval status dictionary
            output_path: Path to save the report
            
        Returns:
            Path to saved report
        """
        try:
            report_content = self._generate_approval_report_content(approval_status)
            
            with open(output_path, 'w') as f:
                f.write(report_content)
            
            logger.info(f"Approval report saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error creating approval report: {str(e)}")
            return ""
    
    def _generate_approval_report_content(self, approval_status: Dict) -> str:
        """Generate approval report content"""
        report = "TEST CASE APPROVAL REPORT\n"
        report += "=" * 70 + "\n\n"
        
        report += f"Total Test Cases: {approval_status['total']}\n"
        report += f"Approved: {approval_status['approved']}\n"
        report += f"Rejected: {approval_status['rejected']}\n"
        report += f"Modified: {approval_status['modified']}\n"
        report += f"Approval Rate: {(approval_status['approved']/approval_status['total']*100):.1f}%\n\n"
        
        report += "DETAILED RESULTS\n"
        report += "-" * 70 + "\n\n"
        
        for detail in approval_status['details']:
            report += f"Test Case: {detail['test_case']}\n"
            report += f"Scenario: {detail['scenario']}\n"
            report += f"Status: {detail['status']}\n"
            if detail['reason']:
                report += f"Reason/Notes: {detail['reason']}\n"
            report += "\n"
        
        return report


class QuickApprovalMode:
    """
    Quick approval mode for bulk operations
    Approves all test cases by default, only prompts for special cases
    """
    
    def __init__(self):
        self.approval_status = {}
    
    def approve_all(self, test_cases: List[TestCase]) -> Tuple[List[TestCase], Dict]:
        """
        Approve all test cases in batch
        
        Args:
            test_cases: List of test cases
            
        Returns:
            Tuple of (all_test_cases, approval_status)
        """
        logger.info("\n" + "="*70)
        logger.info("QUICK APPROVAL MODE - APPROVING ALL TEST CASES")
        logger.info("="*70)
        logger.info(f"Total test cases: {len(test_cases)}\n")
        
        approval_status = {
            "total": len(test_cases),
            "approved": len(test_cases),
            "rejected": 0,
            "modified": 0,
            "mode": "QUICK_APPROVAL_ALL",
            "details": []
        }
        
        for test_case in test_cases:
            approval_status["details"].append({
                "test_case": test_case.test_case_name,
                "scenario": test_case.test_scenario,
                "status": "APPROVED",
                "reason": None
            })
        
        logger.info(f"All {len(test_cases)} test cases APPROVED in quick mode\n")
        return test_cases, approval_status
    
    def selective_approval(self, test_cases: List[TestCase], 
                          reject_if_steps_less_than: int = 2) -> Tuple[List[TestCase], Dict]:
        """
        Approve with conditions (e.g., minimum steps)
        
        Args:
            test_cases: List of test cases
            reject_if_steps_less_than: Reject if steps are less than this
            
        Returns:
            Tuple of (approved_test_cases, approval_status)
        """
        logger.info("\n" + "="*70)
        logger.info("SELECTIVE APPROVAL MODE")
        logger.info("="*70)
        logger.info(f"Criteria: Reject if steps < {reject_if_steps_less_than}\n")
        
        approved_tests = []
        approval_status = {
            "total": len(test_cases),
            "approved": 0,
            "rejected": 0,
            "modified": 0,
            "mode": "SELECTIVE_APPROVAL",
            "criteria": f"Min steps: {reject_if_steps_less_than}",
            "details": []
        }
        
        for test_case in test_cases:
            if len(test_case.steps) >= reject_if_steps_less_than:
                approved_tests.append(test_case)
                approval_status["approved"] += 1
                status = "APPROVED"
            else:
                approval_status["rejected"] += 1
                status = "REJECTED"
                reason = f"Only {len(test_case.steps)} steps, minimum required: {reject_if_steps_less_than}"
            
            approval_status["details"].append({
                "test_case": test_case.test_case_name,
                "scenario": test_case.test_scenario,
                "status": status,
                "reason": reason if status == "REJECTED" else None
            })
        
        logger.info(f"Approved: {approval_status['approved']}")
        logger.info(f"Rejected: {approval_status['rejected']}\n")
        
        return approved_tests, approval_status
