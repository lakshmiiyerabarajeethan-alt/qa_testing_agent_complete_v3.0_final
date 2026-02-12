# QA Testing Agent - File Guide & Reference

Complete reference for all files in the project, organized by category.

## 📚 Documentation Files

### PROJECT_SUMMARY.md
**Purpose**: High-level overview of the entire system
**Contains**: 
- Features summary
- Quick start guide
- Use cases
- Key components
**Who should read**: Everyone - start here!

### README.md
**Purpose**: Complete feature documentation and user guide
**Location**: `qa_testing_agent/README.md`
**Contains**:
- Feature descriptions
- Architecture overview
- Configuration options
- Usage examples
- Best practices
**Who should read**: Users wanting to understand all features

### SETUP_AND_DEPLOYMENT.md
**Purpose**: Installation, configuration, and deployment guide
**Location**: `qa_testing_agent/SETUP_AND_DEPLOYMENT.md`
**Contains**:
- Prerequisites checklist
- Step-by-step installation
- Configuration details
- Testing & validation
- Docker deployment
- CI/CD integration examples
- Troubleshooting guide
**Who should read**: Developers doing setup and deployment

### ARCHITECTURE_AND_FLOW.md
**Purpose**: System architecture and data flow documentation
**Location**: `qa_testing_agent/ARCHITECTURE_AND_FLOW.md` (in outputs)
**Contains**:
- System architecture diagrams
- Data flow diagrams
- Class relationships
- Retry logic flow
- File processing flow
- Configuration hierarchy
- Error handling flow
- Performance characteristics
**Who should read**: Architects and developers understanding system design

### FILE_GUIDE.md
**Purpose**: This file - reference for all files in the project
**Location**: `qa_testing_agent/FILE_GUIDE.md`
**Who should read**: Anyone needing to find a specific file

---

## 🚀 Entry Points

### main.py
**Purpose**: Main entry point for the entire system
**Location**: `qa_testing_agent/main.py`
**What it does**:
1. Initializes all components
2. Parses Excel test cases
3. Runs orchestrator
4. Executes approved tests
5. Generates reports
**How to run**: `python main.py`
**Output**: 
- HTML report in `reports/`
- Logs in `qa_agent.log`

### examples.py
**Purpose**: Demonstrates system usage and capabilities
**Location**: `qa_testing_agent/examples.py`
**What it does**:
- Shows how to create test cases
- Demonstrates mock data generation
- Shows agent workflow
- Shows multi-test orchestration
**How to run**: `python examples.py`
**Output**: Example data and workflows (no actual execution)

---

## 🤖 Agent Files

### requirements_agent.py
**Purpose**: AI agent for requirements analysis
**Location**: `qa_testing_agent/agents/requirements_agent.py`
**Class**: `RequirementsAnalysisAgent`
**Key methods**:
- `analyze(test_case, retry_context)` - Analyzes test requirements
**Uses**: OpenAI API (GPT-4)
**Output**: `RequirementsAnalysis` model
**Responsibilities**:
- Understand test requirements deeply
- Identify edge cases
- Determine test data needs
- Document assumptions

### test_designer_agent.py
**Purpose**: AI agent for test code generation
**Location**: `qa_testing_agent/agents/test_designer_agent.py`
**Class**: `TestDesignerAgent`
**Key methods**:
- `design_test(test_case, requirements, retry_context)` - Generates test code
**Uses**: OpenAI API (GPT-4) + MockDataGenerator
**Output**: `GeneratedTestCase` model
**Responsibilities**:
- Generate Selenium/Playwright Python code
- Create mock test data
- Identify required fixtures
- Estimate test duration

### reviewer_agent.py
**Purpose**: AI agent for test quality assurance
**Location**: `qa_testing_agent/agents/reviewer_agent.py`
**Class**: `ReviewerAgent`
**Key methods**:
- `review(test_case, requirements, generated_test)` - Reviews test code
**Uses**: OpenAI API (GPT-4)
**Output**: `ReviewResult` model
**Responsibilities**:
- Validate test code quality
- Check requirements alignment
- Verify test data validity
- Provide improvement suggestions
- Determine rejection reason (if any)

---

## 📊 Data Models

### models.py
**Purpose**: Define all data structures used in the system
**Location**: `qa_testing_agent/models.py`
**Contains classes**:

| Class | Purpose | Used By |
|-------|---------|---------|
| `TestStep` | Individual test step | TestCase |
| `TestCase` | Input test case from Excel | Parser, Orchestrator |
| `RequirementsAnalysis` | Requirements analysis output | RequirementsAgent |
| `GeneratedTestCase` | Generated test code & data | TestDesignerAgent, Executor |
| `ReviewResult` | Review decision & feedback | ReviewerAgent, Orchestrator |
| `TestExecutionResult` | Single test execution result | TestExecutor, ReportGenerator |
| `TestSuiteResult` | Overall test suite results | ReportGenerator |

**When to use**:
- Import when building data structures
- Reference for API contracts
- Validation with Pydantic

---

## 📋 Input Parsers

### excel_parser.py
**Purpose**: Parse Excel test case files
**Location**: `qa_testing_agent/parsers/excel_parser.py`
**Class**: `TestCaseParser`
**Key methods**:
- `parse_folder()` - Parse all Excel files in input folder
- `_parse_excel(filepath)` - Parse single Excel file
- `get_test_cases()` - Get parsed test cases
**Expected Excel format**:
```
Test Scenario | Test Case | Test Data | Step No. | Step Description | Expected Results
```
**Output**: `List[TestCase]`
**Error handling**:
- Logs missing files
- Handles Excel parsing errors
- Validates structure

---

## 🔧 Generators

### mock_data_generator.py
**Purpose**: Generate realistic mock data for tests
**Location**: `qa_testing_agent/generators/mock_data_generator.py`
**Class**: `MockDataGenerator`
**Key methods**:
- `generate_user_credentials()` - User login data
- `generate_customer_data()` - Customer information
- `generate_financial_data()` - Financial transactions
- `generate_product_data()` - Product information
- `generate_test_data_for_scenario(scenario)` - Scenario-aware data
- `generate_bulk_data(scenario, count)` - Multiple records
**Uses**: Faker library for realistic data
**Output**: Dictionary with test data
**Scenario-aware**:
- "login" → credentials
- "customer" → customer info
- "finance" → transaction data
- "product" → product info
- Generic → basic data

---

## ⚙️ Orchestration

### orchestrator.py
**Purpose**: Coordinate multi-agent workflow
**Location**: `qa_testing_agent/orchestrator.py`
**Class**: `QATestingOrchestrator`
**Key methods**:
- `process_test_case(test_case)` - Process single test
- `process_test_suite(test_cases)` - Process multiple tests
**Workflow**:
1. Call RequirementsAnalysisAgent
2. Call TestDesignerAgent
3. Call ReviewerAgent
4. Handle rejections with retry logic
5. Return results
**Retry logic**:
- DATA_ISSUE: Auto-retry (up to 3 times)
- UI_CHANGE: Stop execution
- REQUIREMENT_MISMATCH: Stop execution
**Output**: List of (GeneratedTestCase, ReviewResult, RejectionHistory)

---

## 🎯 Test Execution

### test_executor.py
**Purpose**: Execute generated test code
**Location**: `qa_testing_agent/executors/test_executor.py`
**Class**: `TestExecutor`
**Key methods**:
- `execute(generated_test)` - Execute single test
- `execute_batch(generated_tests)` - Execute multiple tests
- `_write_test_file()` - Write test code to file
- `_generate_fixture_code()` - Create pytest fixtures
**Execution process**:
1. Write generated code to file
2. Initialize WebDriver
3. Run pytest
4. Capture results
5. Collect screenshots/logs
**Output**: `TestExecutionResult`
**Limitations**:
- Requires WebDriver (Chrome/Firefox)
- Headless or GUI mode configurable
- Timeout: 300 seconds per test

---

## 📊 Report Generation

### report_generator.py
**Purpose**: Generate comprehensive HTML reports
**Location**: `qa_testing_agent/utils/report_generator.py`
**Class**: `HTMLReportGenerator`
**Key methods**:
- `generate_report(test_results, execution_results, suite_id)` - Generate HTML report
- `_build_html()` - Build HTML content
- `_generate_test_details_section()` - Test details
- `_generate_rejection_section()` - Rejection details
- `_get_css()` - CSS styling
**Report contents**:
- Executive summary
- Test details (per test case)
- Review status
- Execution results
- Rejection details & history
- Execution logs
- Screenshots (on failure)
- Metrics (pass rate, duration)
**Output**: HTML file in `reports/` directory
**Styling**: Responsive design with gradient backgrounds

---

## ⚙️ Configuration

### settings.py
**Purpose**: Configuration management
**Location**: `qa_testing_agent/config/settings.py`
**Classes**:
- `RejectionReason` - Enum for rejection reasons
- `TestStatus` - Enum for test status
- `Settings` - Pydantic configuration class
**Configuration variables**:
| Variable | Default | Purpose |
|----------|---------|---------|
| OPENAI_API_KEY | (env var) | OpenAI API key |
| OPENAI_MODEL | gpt-4-turbo | LLM model to use |
| TEST_INPUT_FOLDER | ./test_inputs | Input Excel folder |
| REPORT_OUTPUT_FOLDER | ./reports | Output report folder |
| HEADLESS | False | Headless browser mode |
| MAX_RETRY_LOOPS | 3 | Max retry attempts |
**Load order**:
1. Environment variables
2. .env file
3. Default values

### .env.example
**Purpose**: Template for environment configuration
**Location**: `qa_testing_agent/.env.example`
**Contains**: Template for all environment variables
**How to use**:
```bash
cp .env.example .env
nano .env  # Edit with your settings
```

---

## 📁 Directory Structure

```
qa_testing_agent/
├── 📖 README.md                    # Main documentation
├── 📖 SETUP_AND_DEPLOYMENT.md     # Setup guide
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                 # Environment template
│
├── 🤖 agents/                      # AI agents
│   ├── __init__.py
│   ├── requirements_agent.py      # Phase 1: Analysis
│   ├── test_designer_agent.py     # Phase 2: Design
│   └── reviewer_agent.py          # Phase 3: Review
│
├── 📋 parsers/                     # Input parsing
│   ├── __init__.py
│   └── excel_parser.py            # Excel file parser
│
├── 🔧 generators/                  # Code/data generation
│   ├── __init__.py
│   └── mock_data_generator.py     # Mock data generation
│
├── ⚙️ executors/                    # Test execution
│   ├── __init__.py
│   └── test_executor.py           # Pytest executor
│
├── 📊 utils/                       # Utility modules
│   ├── __init__.py
│   └── report_generator.py        # HTML report generation
│
├── ⚙️ config/                       # Configuration
│   ├── __init__.py
│   └── settings.py                # Configuration settings
│
├── 📚 models.py                     # Data models
├── 🎯 orchestrator.py              # Multi-agent orchestrator
├── 🚀 main.py                      # Entry point
└── 💡 examples.py                  # Usage examples

test_inputs/                        # Input test cases
├── test_cases_1.xlsx
├── test_cases_2.xlsx
└── ...

reports/                            # Generated outputs
├── qa_suite_*.html                # HTML reports
├── screenshots/                    # Failure screenshots
└── test_execution/                # Test files & logs
```

---

## 🔄 Dependency Graph

```
main.py
├── parsers/excel_parser.py
├── orchestrator.py
│   ├── agents/requirements_agent.py
│   ├── agents/test_designer_agent.py
│   │   └── generators/mock_data_generator.py
│   └── agents/reviewer_agent.py
├── executors/test_executor.py
└── utils/report_generator.py

models.py (used by all modules)
config/settings.py (used by all modules)
```

---

## 📝 File Sizes & Complexity

| File | Size | Complexity | Purpose |
|------|------|-----------|---------|
| requirements_agent.py | ~3KB | Medium | LLM integration |
| test_designer_agent.py | ~4KB | High | Code generation |
| reviewer_agent.py | ~3KB | Medium | Quality assurance |
| excel_parser.py | ~3KB | Low | Input parsing |
| mock_data_generator.py | ~3KB | Low | Data generation |
| test_executor.py | ~4KB | High | Test execution |
| report_generator.py | ~12KB | High | HTML generation |
| orchestrator.py | ~6KB | Medium | Workflow orchestration |
| main.py | ~6KB | Medium | Entry point |
| models.py | ~3KB | Low | Data structures |
| settings.py | ~2KB | Low | Configuration |

---

## 🔍 Where to Make Changes

### Add new test scenario support
**File**: `generators/mock_data_generator.py`
**Method**: `generate_test_data_for_scenario()`
**Change**: Add new scenario condition

### Customize report format
**File**: `utils/report_generator.py`
**Method**: `_get_css()` or `_build_html()`
**Change**: Modify HTML/CSS structure

### Change LLM prompts
**Files**: 
- `agents/requirements_agent.py`
- `agents/test_designer_agent.py`
- `agents/reviewer_agent.py`
**Method**: `_build_prompt()` or `_get_review_from_llm()`
**Change**: Modify system/user prompts

### Add new configuration option
**File**: `config/settings.py`
**Class**: `Settings`
**Change**: Add new field to Settings class

### Support different Excel format
**File**: `parsers/excel_parser.py`
**Method**: `_parse_excel()`
**Change**: Update column mapping logic

### Modify retry logic
**File**: `orchestrator.py`
**Method**: `process_test_case()`
**Change**: Update retry conditions

---

## 🧪 Testing & Validation

### To test individual modules:
```bash
# Test parser
python -c "from parsers.excel_parser import TestCaseParser; ..."

# Test agents
python examples.py

# Test full pipeline
python main.py
```

### To debug:
```bash
# Check logs
tail -f qa_agent.log

# Run with verbose output
python main.py  # Logs to both console and file
```

---

## 📈 Maintenance

### Regular maintenance tasks:
1. **Monthly**: Clean up old reports in `reports/`
2. **Quarterly**: Review and optimize prompts
3. **As needed**: Update dependencies in `requirements.txt`
4. **After changes**: Run `python examples.py` to validate

### Performance monitoring:
- Check `qa_agent.log` for execution times
- Monitor HTML report metrics (pass rate, duration)
- Track API usage and costs

---

## 🎓 Learning Path

1. **Start here**: PROJECT_SUMMARY.md
2. **Understand architecture**: ARCHITECTURE_AND_FLOW.md
3. **Setup system**: SETUP_AND_DEPLOYMENT.md
4. **Read examples**: examples.py
5. **Review main flow**: main.py
6. **Study agents**: agents/*.py
7. **Explore models**: models.py

---

**Last Updated**: February 2024
**Version**: 1.0
