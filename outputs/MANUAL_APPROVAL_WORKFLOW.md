# Manual Approval Workflow Guide

## Overview

The QA Testing Agent now includes a **mandatory manual approval step** after test case generation but before execution. This ensures all AI-generated test scenarios are reviewed and approved by QA before the expensive test execution phase.

```
Azure DevOps Stories
    ↓
Generate Test Cases (AI)
    ↓
Save to Excel
    ↓
⏸️ MANUAL APPROVAL (QA Review)
    ├─ Option 1: APPROVE ✓
    ├─ Option 2: MANUAL REVIEW (modify Excel)
    ├─ Option 3: REJECT (regenerate)
    └─ Option 4: REQUEST REVISIONS (AI revises)
    ↓
Continue with Pipeline
    ├─ Parse → Analyze → Design → Review → Execute
    ↓
HTML Report
```

---

## Why Manual Approval?

✅ **Quality Control** - QA validates test scenario coverage
✅ **Cost Saving** - Prevents execution of invalid test cases
✅ **Risk Mitigation** - Catches AI misinterpretations early
✅ **Coverage Verification** - Ensures all requirements are tested
✅ **Edge Cases** - QA can identify missing scenarios

---

## Approval Workflow Steps

### Step 1: Test Case Generation Completes

```
[Phase 4] Saving test cases to Excel...
✓ Test cases saved to test_inputs/devops_tests_20240210_143022.xlsx
```

### Step 2: Approval Workflow Starts

```
[Phase 5] Manual test case approval workflow...

======================================================================
TEST CASE GENERATION SUMMARY
======================================================================

Generated From: 3 user stories
Total Test Cases: 9
Total Scenarios: 3
Total Test Steps: 45

----------------------------------------------------------------------
SCENARIOS GENERATED:
----------------------------------------------------------------------

📋 Login Feature
   Test Cases: 3
   Total Steps: 12
   ├─ test_login_happy_path (4 steps)
   ├─ test_login_invalid_credentials (4 steps)
   └─ test_login_session_timeout (4 steps)

📋 User Profile
   Test Cases: 3
   Total Steps: 15
   ├─ test_profile_update (5 steps)
   ├─ test_profile_permissions (5 steps)
   └─ test_profile_data_validation (5 steps)

...

======================================================================
EXCEL FILE LOCATION:
test_inputs/devops_tests_20240210_143022.xlsx
======================================================================

📝 PLEASE REVIEW THE EXCEL FILE FOR:
   • All test scenarios from stories are covered
   • All acceptance criteria are tested
   • Test steps are clear and actionable
   • Expected results are properly defined
   • Test data is appropriate
   • No duplicate test cases
   • Edge cases and error scenarios included
```

### Step 3: User Makes Decision

```
======================================================================
APPROVAL DECISION
======================================================================

1. ✓ APPROVE - Test cases look good, continue with execution
2. 🔍 REVIEW - I need to manually review/modify the Excel file
3. ✗ REJECT - Test cases need to be regenerated
4. ⚠️  REVISIONS - Request specific revisions from AI

Select option (1-4): [your choice]
```

---

## Decision Options & Outcomes

### Option 1: APPROVE ✓

**What to do**: Review Excel and confirm all test scenarios are adequate

**Outcome**: 
- System continues immediately with test execution
- Test cases are parsed from Excel
- Analysis, design, review phases execute
- Tests execute automatically
- Report is generated

**Time**: Saves time by proceeding directly to execution

```bash
Select option (1-4): 1

✓ Test cases APPROVED - continuing with execution...

[Phase 6] Running analysis and design pipeline...
[Phase 7] Executing approved tests...
[Phase 8] Generating final report...
✓ Report: reports/devops_suite_20240210_143022_report.html
```

### Option 2: REVIEW (Manual Changes)

**What to do**: Review Excel, make modifications, then resume

**Outcome**:
- System pauses and waits
- Excel file location is displayed
- You manually review and modify Excel
- Save your changes
- Run system again to continue
- System detects modified Excel and resumes

**Time**: Takes additional time for manual review but ensures accuracy

```bash
Select option (1-4): 2

⏸️ Manual review requested

Next steps:
1. Review and modify the Excel file
2. Run the system again to continue
   File: test_inputs/devops_tests_20240210_143022.xlsx

--- USER REVIEWS AND MODIFIES EXCEL ---

$ python main.py  # Run again
# System detects modified Excel
# Continues automatically

[Phase 6] Running analysis and design pipeline...
```

**What to modify in Excel**:
- Add/remove test cases
- Modify test step descriptions
- Update expected results
- Add/remove test scenarios
- Adjust test data
- Rename test cases

### Option 3: REJECT

**What to do**: Test cases need to be regenerated with different approach

**Outcome**:
- System logs rejection reason
- Workflow stops
- Options to continue:
  1. Modify Excel manually and run again
  2. Run Azure DevOps integration with feedback

**Time**: Requires restart of process

```bash
Select option (1-4): 3

✗ Test cases REJECTED

Provide rejection reason (for logging): 
"Missing edge cases for payment validation, need more negative scenarios"

--- REJECTION LOGGED ---

Next steps:
1. Modify Excel file manually and run again, OR
2. Run Azure DevOps again with feedback context

$ python main.py
# Select Option 1: Azure DevOps with feedback
```

### Option 4: REQUEST REVISIONS

**What to do**: Request specific revisions from the AI test case generator

**Outcome**:
- System logs revision request with details
- Workflow stops
- Options:
  1. Modify Excel directly based on feedback
  2. Run Azure DevOps again with revision context
  3. Manually fix issues

**Time**: Requires either manual fixes or re-running generation

```bash
Select option (1-4): 4

⚠️  Revisions requested.

Describe required revisions:
"Add comprehensive error handling tests, include database failure scenarios"

--- REVISION REQUEST LOGGED ---

Next steps:
1. Run Azure DevOps again to regenerate with feedback, OR
2. Manually modify the Excel file based on revision request

$ python main.py
# Continue with Excel modifications or regeneration
```

---

## Approval Checklist

Use this checklist when reviewing test cases:

### Coverage Analysis
- [ ] All user stories are covered
- [ ] All acceptance criteria have test cases
- [ ] No gaps in requirement coverage
- [ ] Acceptance criteria clearly mapped to test steps

### Test Quality
- [ ] Test steps are clear and actionable
- [ ] Test steps are unambiguous
- [ ] Expected results are well-defined
- [ ] Test data is realistic and appropriate
- [ ] No duplicate test cases
- [ ] Tests follow naming conventions

### Scenario Coverage
- [ ] Happy path scenarios included
- [ ] Edge case scenarios included
- [ ] Error/negative scenarios included
- [ ] Boundary condition tests included
- [ ] Performance tests (if applicable)
- [ ] Security tests (if applicable)

### Test Data
- [ ] Test data is valid and realistic
- [ ] Data covers all scenarios
- [ ] Sensitive data handled appropriately
- [ ] Data setup/cleanup documented

### Overall Quality
- [ ] Test cases well-organized
- [ ] Scenarios logically grouped
- [ ] Test cases independent
- [ ] Total number of tests reasonable
- [ ] Tests maintainable long-term

---

## Workflow Examples

### Example 1: Immediate Approval

```
User Story: "User can login"
    ↓ Generate
Test Cases: Login happy path, invalid credentials, session timeout
    ↓ Review (2 minutes)
"Looks good, covers all scenarios"
    ↓ APPROVE
Execution starts immediately
    ↓
Report generated (20 min total)
```

### Example 2: Manual Review & Modification

```
User Story: "User can search products"
    ↓ Generate
Test Cases: Search by name, empty result, special characters
    ↓ Review
"Missing sorting and filtering tests"
    ↓ REVIEW OPTION
System pauses, Excel location shown
    ↓ User Modifies Excel
Add 3 new test cases for sorting/filtering
    ↓ Save & Run Again
System continues
    ↓
Execution with all scenarios
    ↓
Report generated (45 min total)
```

### Example 3: Request Revisions

```
User Stories: Multiple payment scenarios
    ↓ Generate
Test Cases: Basic payment flow
    ↓ Review
"Missing error scenarios, network failures, timeout handling"
    ↓ REVISIONS OPTION
Log: "Add comprehensive error handling tests"
    ↓ Manual Excel Updates (or)
Regenerate with feedback
    ↓
Execution
    ↓
Report generated
```

---

## Approval Logs

### Approval Log File

After each approval decision, a JSON log is created:

```json
{
  "timestamp": "2024-02-10T14:30:22.123456",
  "stories_processed": 3,
  "total_test_cases": 9,
  "total_scenarios": 3,
  "total_steps": 45,
  "scenarios": {
    "Login Feature": {
      "test_cases": [...],
      "step_count": 12
    }
  },
  "approval_decision": "APPROVED",
  "decision_timestamp": "2024-02-10T14:35:15.654321",
  "excel_path": "test_inputs/devops_tests_20240210_143022.xlsx"
}
```

**Location**: `approval_logs/approval_log_YYYYMMDD_HHMMSS.json`

---

## Key Features

### Approval Summary
```
Generated From: X user stories
Total Test Cases: Y
Total Scenarios: Z
Total Test Steps: W
```

### Scenario Breakdown
Shows each scenario and its test cases:
```
📋 Scenario Name
   Test Cases: N
   Total Steps: M
   ├─ test_case_1 (X steps)
   ├─ test_case_2 (Y steps)
   └─ test_case_3 (Z steps)
```

### Excel File Location
Clearly shows where the Excel file is saved for review

### Approval Checklist
Built-in checklist for manual review guidelines

---

## Best Practices

### For QA Reviewers

1. **Check Coverage** - Ensure all acceptance criteria are tested
2. **Validate Scenarios** - Verify happy path + edge cases + errors
3. **Review Data** - Check test data is realistic
4. **Check Clarity** - Ensure test steps are understandable
5. **Detect Duplicates** - Remove any duplicate test cases
6. **Assess Completeness** - Look for missing scenarios

### For Revision Requests

1. **Be Specific** - "Add timeout handling tests"
2. **Be Actionable** - "Include negative test cases for validation"
3. **Be Clear** - Specify exact scenarios needed
4. **Reference Stories** - "From story #12345, acceptance criterion..."

### For Manual Modifications

1. **Keep Consistent** - Follow existing naming conventions
2. **Maintain Format** - Use same Excel format
3. **Document Changes** - Note what you added/removed
4. **Test Validity** - Ensure new tests are valid

---

## Approval Decision Guide

| Scenario | Best Option |
|----------|------------|
| Excellent coverage, clear steps | APPROVE |
| Missing 1-2 scenarios, data issues | REVIEW (modify Excel) |
| Major gaps, needs rethinking | REJECT |
| Minor improvements needed | REVISIONS |
| Unclear test steps but good coverage | REVIEW (clarify steps) |
| Acceptable but needs expert review | REVIEW (modify) |

---

## Troubleshooting

### "Excel file won't open"

```bash
# Manual opening
Windows: Double-click the file
Mac: Right-click → Open With → Excel
Linux: libreoffice path/to/file.xlsx
```

### "Don't know what to modify"

1. Check the approval checklist
2. Compare with original user stories
3. Verify all acceptance criteria covered
4. Look for missing edge cases

### "Want to completely regenerate"

```bash
# Option 1: Run Azure DevOps again
python main.py
Select: 1. Azure DevOps
Re-enter credentials and area/iteration

# Option 2: Delete Excel and run again
rm test_inputs/devops_tests_*.xlsx
python main.py
```

### "How long should approval take?"

- **Simple story (1-2 scenarios)**: 5-10 minutes
- **Medium story (3-5 scenarios)**: 15-30 minutes
- **Complex story (5+ scenarios)**: 30-60 minutes

---

## Integration with CI/CD

For automated CI/CD, you can:

1. **Auto-approve** in non-interactive mode:
```bash
APPROVAL_MODE=auto python main.py
```

2. **Skip approval** for testing:
```bash
SKIP_APPROVAL=true python main.py
```

3. **Require approval** and create artifact:
```bash
APPROVAL_MODE=manual python main.py
# Save Excel artifact for review
```

---

## Approval Workflow Summary

```
Generate Test Cases
    ↓
Display Summary
    ↓
Get User Decision
    ├─ APPROVE → Execute
    ├─ REVIEW → Pause for manual changes
    ├─ REJECT → Stop and log
    └─ REVISIONS → Request feedback
    ↓
Log Decision
    ↓
Continue or Stop
```

---

## Next Steps After Approval

### If APPROVED
1. System continues automatically
2. Parsing test cases from Excel
3. Running analysis and design
4. Executing tests
5. Generating HTML report

### If REVIEW/REVISIONS
1. System pauses and shows Excel location
2. User reviews/modifies Excel
3. User saves changes
4. User runs system again
5. System detects changes and continues

### If REJECTED
1. Workflow stops
2. Rejection reason is logged
3. User can:
   - Manually fix Excel and run again
   - Regenerate from Azure DevOps with feedback
   - Manually create new test cases

---

**Manual Approval Workflow v1.0**

*Critical quality gate for test case generation and execution.*

**Status**: ✅ Integrated  
**Availability**: For Azure DevOps input source  
**Recommendation**: Always review generated test cases before execution
