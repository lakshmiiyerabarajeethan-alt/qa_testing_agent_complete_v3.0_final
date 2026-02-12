# QA Testing Agent - Architecture & Flow Documentation

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         QA TESTING AGENT                             │
│                    Multi-Agent Orchestration System                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  INPUT LAYER                                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📁 test_inputs/                                                    │
│     ├── test_cases_1.xlsx  ──┐                                      │
│     ├── test_cases_2.xlsx  ──┤                                      │
│     └── test_cases_n.xlsx  ──┼─→ Excel Parser → [TestCase Model]   │
│                              │    (parsers/excel_parser.py)         │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER                                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  QATestingOrchestrator (orchestrator.py)                             │
│  ├─ Sequential Processing                                           │
│  ├─ Retry Logic                                                     │
│  └─ Error Handling                                                  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    AGENT PIPELINE                           │    │
│  │                                                             │    │
│  │  ┌──────────────────────────────────────────────────┐      │    │
│  │  │  PHASE 1: Requirements Analysis                 │      │    │
│  │  │  (agents/requirements_agent.py)                 │      │    │
│  │  │                                                  │      │    │
│  │  │  Input: TestCase                                │      │    │
│  │  │  ↓                                               │      │    │
│  │  │  Uses OpenAI GPT-4 to:                          │      │    │
│  │  │  • Understand test requirements                 │      │    │
│  │  │  • Identify edge cases                          │      │    │
│  │  │  • Determine test data needs                    │      │    │
│  │  │  • Document assumptions                         │      │    │
│  │  │  ↓                                               │      │    │
│  │  │  Output: RequirementsAnalysis                   │      │    │
│  │  │  {                                              │      │    │
│  │  │    scenario_understanding: str,                 │      │    │
│  │  │    identified_requirements: List[str],          │      │    │
│  │  │    test_data_needs: Dict,                       │      │    │
│  │  │    assumptions: List[str]                       │      │    │
│  │  │  }                                              │      │    │
│  │  └──────────────────────────────────────────────────┘      │    │
│  │                        ↓                                    │    │
│  │  ┌──────────────────────────────────────────────────┐      │    │
│  │  │  PHASE 2: Test Design & Code Generation         │      │    │
│  │  │  (agents/test_designer_agent.py)                │      │    │
│  │  │                                                  │      │    │
│  │  │  Input: TestCase + RequirementsAnalysis        │      │    │
│  │  │  ↓                                               │      │    │
│  │  │  1. Generate Mock Data                          │      │    │
│  │  │     └─ generators/mock_data_generator.py        │      │    │
│  │  │        • Faker for realistic data               │      │    │
│  │  │        • Scenario-aware generation              │      │    │
│  │  │                                                  │      │    │
│  │  │  2. Generate Test Code                          │      │    │
│  │  │     └─ Uses OpenAI GPT-4 to generate:           │      │    │
│  │  │        • Selenium/Playwright Python code        │      │    │
│  │  │        • Pytest fixtures                        │      │    │
│  │  │        • Assertions for each step               │      │    │
│  │  │        • Error handling                         │      │    │
│  │  │        • Screenshot on failure                  │      │    │
│  │  │                                                  │      │    │
│  │  │  Output: GeneratedTestCase                      │      │    │
│  │  │  {                                              │      │    │
│  │  │    test_code: str,                              │      │    │
│  │  │    test_data: Dict,                             │      │    │
│  │  │    fixtures: List[str],                         │      │    │
│  │  │    estimated_duration: int                      │      │    │
│  │  │  }                                              │      │    │
│  │  └──────────────────────────────────────────────────┘      │    │
│  │                        ↓                                    │    │
│  │  ┌──────────────────────────────────────────────────┐      │    │
│  │  │  PHASE 3: Review & Quality Assurance            │      │    │
│  │  │  (agents/reviewer_agent.py)                     │      │    │
│  │  │                                                  │      │    │
│  │  │  Input: TestCase + RequirementsAnalysis +       │      │    │
│  │  │         GeneratedTestCase                       │      │    │
│  │  │  ↓                                               │      │    │
│  │  │  Uses OpenAI GPT-4 to review:                   │      │    │
│  │  │  • Code quality & correctness                   │      │    │
│  │  │  • Requirements alignment                       │      │    │
│  │  │  • Test data validity                           │      │    │
│  │  │  • Flakiness & reliability                      │      │    │
│  │  │  • Error handling adequacy                      │      │    │
│  │  │  • Best practices compliance                    │      │    │
│  │  │  ↓                                               │      │    │
│  │  │  Output: ReviewResult                           │      │    │
│  │  │  {                                              │      │    │
│  │  │    is_approved: bool,                           │      │    │
│  │  │    rejection_reason: RejectionReason,           │      │    │
│  │  │    rejection_details: str,                      │      │    │
│  │  │    improvement_suggestions: str                 │      │    │
│  │  │  }                                              │      │    │
│  │  └──────────────────────────────────────────────────┘      │    │
│  │                        ↓                                    │    │
│  │                   DECISION POINT                           │    │
│  │                        ↓                                    │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                       │
│                    ┌─────────────────┬─────────────────┐            │
│                    │                 │                 │            │
│                    ▼                 ▼                 ▼            │
│              ✓ APPROVED        ✗ REJECTED        ↻ RETRY          │
│                    │                 │                 │            │
│                    │          ┌──────┴──────┐         │            │
│                    │          │             │         │            │
│                    │      DATA_ISSUE    UI_CHANGE     │            │
│                    │          │             │         │            │
│                    │      ┌───▼──┐      ┌──▼──┐      │            │
│                    │      │ Retry │      │Stop │      │            │
│                    │      │ Loop  │      │Report    │            │
│                    │      │(up to │      │(Manual   │            │
│                    │      │ 3x)   │      │ Fix)     │            │
│                    │      └───┬──┘      └──┬──┘      │            │
│                    │          │             │         │            │
│                    └──────────┼─────────────┼─────────┘            │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  EXECUTION LAYER                                                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Approved Tests Only → TestExecutor (executors/test_executor.py)    │
│                                                                       │
│  ┌──────────────────────────────────────────────┐                  │
│  │  1. Write generated code to test file        │                  │
│  │  2. Setup pytest environment                 │                  │
│  │  3. Initialize WebDriver (Chrome/Firefox)    │                  │
│  │  4. Execute test steps                       │                  │
│  │  5. Capture screenshots on failure           │                  │
│  │  6. Generate test reports                    │                  │
│  │  7. Collect results and logs                 │                  │
│  └──────────────────────────────────────────────┘                  │
│                        ↓                                            │
│  Output: TestExecutionResult                                        │
│  {                                                                  │
│    test_name: str,                                                 │
│    status: TestStatus,                                             │
│    duration_seconds: float,                                        │
│    error_message: Optional[str],                                   │
│    screenshot_path: Optional[str],                                 │
│    logs: List[str]                                                 │
│  }                                                                  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  REPORTING LAYER                                                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  HTMLReportGenerator (utils/report_generator.py)                    │
│         ↓                                                            │
│  Combines:                                                          │
│  • Design Results (approved/rejected + reasons)                     │
│  • Execution Results (passed/failed + metrics)                      │
│  • Screenshots (on failure)                                         │
│  • Logs (detailed execution logs)                                   │
│         ↓                                                            │
│  Generates: Professional HTML Report                                │
│  📄 reports/qa_suite_YYYYMMDD_HHMMSS_report.html                    │
│                                                                       │
│  Contains:                                                          │
│  ✓ Executive Summary                                                │
│  ✓ Test Details (scenario, steps, data)                             │
│  ✓ Review Status (approved/rejected)                                │
│  ✓ Execution Results (passed/failed)                                │
│  ✓ Rejection Details (with history)                                 │
│  ✓ Metrics (pass rate, duration, coverage)                          │
│  ✓ Screenshots & Logs                                               │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  OUTPUT LAYER                                                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  📁 reports/                                                         │
│     ├── qa_suite_YYYYMMDD_HHMMSS_report.html  (Main Report)         │
│     ├── screenshots/                          (Failure Screenshots)  │
│     │   └── failure_screenshot_001.png                              │
│     └── test_execution/                       (Test Files & Logs)   │
│         ├── test_scenario_001.py                                    │
│         └── report_scenario_001.html                                │
│                                                                       │
│  📄 qa_agent.log                              (Execution Logs)       │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────┐
│ Excel Files │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ TestCaseParser   │ (parsers/excel_parser.py)
└──────┬───────────┘
       │ List[TestCase]
       ▼
┌──────────────────────────┐
│ QATestingOrchestrator    │ (orchestrator.py)
│                          │
│ for each TestCase:       │
│                          │
│  ┌────────────────────┐  │
│  │ RequirementsAgent  │  │ Uses: OpenAI API
│  └────────────────────┘  │
│           ↓               │
│  ┌────────────────────┐  │
│  │ TestDesignerAgent  │  │ Uses: OpenAI API + MockDataGenerator
│  │   + DataGenerator  │  │
│  └────────────────────┘  │
│           ↓               │
│  ┌────────────────────┐  │
│  │ ReviewerAgent      │  │ Uses: OpenAI API
│  │                    │  │
│  │ if approved:       │  │
│  │   continue ────────┼────────┐
│  │                    │        │
│  │ if data issue:     │        │
│  │   retry ──────────┐│        │
│  │   (feedback loop) ││        │
│  │                    │        │
│  │ if ui_change:      │        │
│  │   stop + report    │        │
│  └────────────────────┘        │
│                                │
│ Returns: GeneratedTestCase +   │
│          ReviewResult +        │
│          RejectionHistory      │
└────────────────────────────────┘
       │
       └─────────────────────────────┐
                                     │
       ┌─────────────────────────────┘
       │
       ▼
    (Approved Tests Only)
       │
       ▼
┌──────────────────────────┐
│ TestExecutor             │ (executors/test_executor.py)
│                          │
│ for each ApprovedTest:   │
│  1. Write to test_*.py   │
│  2. Run pytest           │
│  3. Capture results      │
│  4. Collect screenshots  │
└──────────────────────────┘
       │
       ▼ List[TestExecutionResult]
       │
       ▼
┌──────────────────────────┐
│ HTMLReportGenerator      │ (utils/report_generator.py)
└──────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│ HTML Report + Assets     │
│ (Screenshots + Logs)     │
└──────────────────────────┘
```

---

## Class Relationships

```
models.py (Data Models)
├── TestStep
│   └── step_no: int
│   └── description: str
│   └── expected_results: str
│
├── TestCase (Input)
│   └── test_scenario: str
│   └── test_case_name: str
│   └── steps: List[TestStep]
│
├── RequirementsAnalysis (Phase 1 Output)
│   └── test_case_id: str
│   └── scenario_understanding: str
│   └── identified_requirements: List[str]
│   └── test_data_needs: Dict
│   └── assumptions: List[str]
│
├── GeneratedTestCase (Phase 2 Output)
│   └── test_case_id: str
│   └── test_code: str (Python code)
│   └── test_data: Dict (Generated mock data)
│   └── fixtures: List[str]
│   └── estimated_duration: int
│
├── ReviewResult (Phase 3 Output)
│   └── test_case_id: str
│   └── is_approved: bool
│   └── rejection_reason: RejectionReason
│   └── rejection_details: str
│   └── improvement_suggestions: str
│
├── TestExecutionResult (Execution Output)
│   └── test_case_id: str
│   └── status: TestStatus (PASSED/FAILED)
│   └── duration_seconds: float
│   └── error_message: Optional[str]
│   └── screenshot_path: Optional[str]
│   └── logs: List[str]
│
└── TestSuiteResult (Final Output)
    └── total_tests: int
    └── passed_count: int
    └── failed_count: int
    └── test_results: List[TestExecutionResult]
```

---

## Retry Logic Flow

```
Test Case Input
       │
       ▼
Attempt 1: Requirements → Design → Review
       │
       ├─ APPROVED? ──YES──→ Execute ──→ Done
       │                                (Success)
       │
       └─ REJECTED
           │
           ├─ DATA_ISSUE?
           │   │
           │   └─YES─→ Attempt 2: Requirements → Design → Review
           │           (with feedback context)
           │           │
           │           ├─ APPROVED? ──YES──→ Execute ──→ Done
           │           │
           │           └─ REJECTED (same or different issue)
           │               │
           │               ├─ DATA_ISSUE? (again)
           │               │   │
           │               │   └─YES─→ Attempt 3: (final attempt)
           │               │           │
           │               │           ├─ APPROVED? ──→ Execute ──→ Done
           │               │           │
           │               │           └─ REJECTED ──→ Report Failure
           │               │                           (Max Retries)
           │               │
           │               └─ OTHER_REASON ──→ Report Failure
           │
           ├─ UI_CHANGE?
           │   │
           │   └─YES──→ STOP EXECUTION
           │           Report: "UI Change Detected"
           │           Action: Manual fix required
           │
           └─ REQUIREMENT_MISMATCH?
               │
               └─YES──→ STOP EXECUTION
                       Report: "Requirement Mismatch"
                       Action: Review and correct test case
```

---

## File Processing Flow

```
test_inputs/
├── test_file_1.xlsx
├── test_file_2.xlsx
└── test_file_n.xlsx
       │
       ▼
Excel Parser
(parsers/excel_parser.py)
       │
       ├─ Opens each .xlsx file
       ├─ Reads all sheets
       ├─ Maps columns to TestCase model
       ├─ Extracts test steps
       ├─ Groups steps by test scenario
       └─ Returns List[TestCase]
       │
       ▼
Quality Checks:
├─ ✓ Test scenario name present
├─ ✓ Test case name present
├─ ✓ At least one step
├─ ✓ Step descriptions not empty
└─ ✓ Expected results defined
       │
       ▼
Orchestrator Processing
(Sequential per test case)
       │
       ├─ TEST 1: Login
       │   ├─ Phase 1: Analyze Requirements
       │   ├─ Phase 2: Design Test
       │   ├─ Phase 3: Review
       │   └─ → Approve/Reject
       │
       ├─ TEST 2: Customer Management
       │   ├─ Phase 1: Analyze Requirements
       │   ├─ Phase 2: Design Test
       │   ├─ Phase 3: Review
       │   └─ → Approve/Reject
       │
       └─ TEST N: ...
       │
       ▼
Execution Phase
(Approved tests only)
       │
       ├─ Generate pytest code
       ├─ Setup WebDriver
       ├─ Execute steps
       ├─ Capture screenshots
       └─ Collect results
       │
       ▼
Report Generation
(utils/report_generator.py)
       │
       ├─ Compile design results
       ├─ Add execution results
       ├─ Include screenshots
       ├─ Add logs and metrics
       └─ Generate HTML
       │
       ▼
📄 reports/
   └── qa_suite_*.html
   └── screenshots/
   └── test_execution/
```

---

## Configuration Hierarchy

```
Settings Priority (Highest to Lowest):

1. Environment Variables
   OPENAI_API_KEY=sk-...
   HEADLESS=true

2. .env File
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4

3. Python Config (config/settings.py)
   class Settings(BaseSettings):
       OPENAI_API_KEY: str = os.getenv(...)
       HEADLESS: bool = False

4. Defaults
   (Built-in class defaults)
```

---

## OpenAI API Usage

```
Per Test Case (Approximate Tokens):

Phase 1: Requirements Analysis
├─ Input: Test case description (~300 tokens)
├─ System prompt (~500 tokens)
├─ Output: Analysis (~500-800 tokens)
└─ Total: ~1,300-1,600 tokens

Phase 2: Test Design
├─ Input: Requirements + context (~400 tokens)
├─ System prompt (~500 tokens)
├─ Output: Python code (~1,200-1,500 tokens)
└─ Total: ~2,100-2,400 tokens

Phase 3: Review
├─ Input: Code + context (~400 tokens)
├─ System prompt (~500 tokens)
├─ Output: Review (~300-500 tokens)
└─ Total: ~1,200-1,400 tokens

TOTAL PER TEST CASE: ~4,600-5,400 tokens
COST (gpt-4-turbo): ~$0.15-0.20 per test case
```

---

## Performance Characteristics

```
Typical Timeline (per test case):

Requirements Analysis:    2-3 seconds  (API call + processing)
Test Code Generation:     3-4 seconds  (API call + code gen)
Review:                   2-3 seconds  (API call + validation)
Subtotal (Design):        7-10 seconds

Test Execution:           10-30 seconds (depends on app speed)
Report Generation:        1-2 seconds

TOTAL PER TEST CASE:      ~20-45 seconds

Batch Processing (10 tests):  ~5-10 minutes
Batch Processing (50 tests):  ~20-50 minutes
Batch Processing (100+ tests): Consider parallel execution
```

---

## Error Handling Flow

```
Exception Occurs
       │
       ├─ JSONDecodeError
       │   └─ Log error
       │   └─ Retry request
       │   └─ If persists: Report failure
       │
       ├─ TimeoutError
       │   └─ Log timeout
       │   └─ Increase timeout
       │   └─ Or: Report failure
       │
       ├─ APIError
       │   └─ Check API status
       │   └─ Verify API key
       │   └─ Check rate limits
       │   └─ Report failure
       │
       ├─ FileNotFoundError
       │   └─ Check test_inputs folder
       │   └─ Verify Excel file exists
       │   └─ Report path error
       │
       └─ Generic Exception
           └─ Log full traceback
           └─ Continue with next test
           └─ Report in summary
```

---

This architecture ensures:
✅ Modularity - Each component has a single responsibility
✅ Scalability - Can handle many test cases
✅ Flexibility - Easy to extend agents or add new features
✅ Reliability - Error handling and retry logic
✅ Transparency - Comprehensive logging and reporting
