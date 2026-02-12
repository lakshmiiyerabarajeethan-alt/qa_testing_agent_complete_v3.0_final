# QA Testing Agent - Multi-Agent Automated Testing System

A sophisticated end-to-end automated QA testing system that uses multi-agent orchestration with OpenAI to intelligently generate, review, and execute Selenium/Playwright UI tests from test case specifications.

## 🎯 Features

### Multi-Agent Architecture
- **Requirements Analysis Agent**: Deep understanding of test requirements and edge cases
- **Test Designer Agent**: Generates production-ready Selenium/Playwright Python code
- **Reviewer Agent**: Quality assurance and approval/rejection workflow

### Intelligent Workflows
- Sequential pipeline: Requirements → Design → Review → Execution
- Auto-retry logic for data issues with context feedback
- Manual intervention prompts for UI changes
- Comprehensive rejection tracking and reporting

### Mock Data & Fixtures
- Automatic test data generation using Faker
- Scenario-aware data generation (login, customer, financial, product)
- Parameterized test support
- Fixture management and auto-injection

### Comprehensive Reporting
- Professional HTML reports with CSS styling
- Test scenario details and step-by-step execution
- Coverage metrics and pass/fail rates
- Screenshot capture on failures
- Rejection reasons and improvement suggestions
- Execution logs and detailed debugging information

### Error Handling
- Graceful failure handling with detailed error messages
- Automatic retry with modified data for data-related issues
- UI change detection with execution stop
- Comprehensive logging (file and console)

## 📋 Architecture

```
┌─────────────────────┐
│  Excel Test Cases   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Test Case Parser   │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────────────┐
│     QA Testing Orchestrator          │
│  ┌──────────────────────────────┐   │
│  │ Requirements Analysis Agent  │   │
│  └──────────┬───────────────────┘   │
│             │                        │
│  ┌──────────▼───────────────────┐   │
│  │    Test Designer Agent       │   │
│  └──────────┬───────────────────┘   │
│             │                        │
│  ┌──────────▼───────────────────┐   │
│  │    Reviewer Agent            │   │
│  │  (Approval/Rejection)        │   │
│  └──────────┬───────────────────┘   │
└─────────────┼──────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
     ▼                 ▼
 APPROVED        REJECTED
     │                 │
     ▼                 ▼
[Execution]      [Reporting]
     │                 │
     └────────┬────────┘
              │
              ▼
      [HTML Report]
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone/setup project
cd qa_testing_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download browser drivers
playwright install  # or chromedriver for Selenium
```

### 2. Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: GPT model to use (e.g., gpt-4-turbo-preview)

### 3. Prepare Test Cases

Create test input folder with Excel files:

```bash
mkdir test_inputs
# Copy your Excel test case files here
```

Excel Format (must match structure):
```
Test Scenario | Test Case | Test Data | Step No. | Step Description | Expected Results | ...
```

See the provided `Metsa_Version_upgrade_DEV.xlsx` for format reference.

### 4. Run Pipeline

```bash
python main.py
```

This will:
1. Parse all Excel test cases
2. Analyze requirements with AI
3. Generate test code with AI
4. Review test code with AI
5. Execute approved tests
6. Generate HTML report

## 📊 Report Structure

The generated HTML report includes:

- **Executive Summary**: Total tests, approval rate, pass rate
- **Test Details**: Each test with status, approval info, test data
- **Execution Results**: Pass/fail status, duration, error messages
- **Rejection Details**: Reasons for rejection and retry history
- **Execution Logs**: Detailed logs from test execution
- **Screenshots**: Failure screenshots for debugging

## 🔄 Retry Logic

### Data Issue Rejection
- **Trigger**: When test data is invalid or incomplete
- **Action**: Auto-retry with corrected data
- **Max Attempts**: Configurable (default: 3)

### UI Change Rejection
- **Trigger**: When UI elements or selectors have changed
- **Action**: Stop execution immediately
- **Report**: Includes detailed UI change information
- **Manual Intervention**: Required to fix test case

### Requirement Mismatch
- **Trigger**: When test doesn't match requirements
- **Action**: Stop execution
- **Report**: Detailed mismatch information

## 📝 Test Case Flow

```
Input Test Case
    │
    ▼
Requirements Analysis
    │ Extract: Requirements, Edge Cases, Data Needs
    ▼
Test Design
    │ Generate: Python Code, Test Data, Fixtures
    ▼
Review
    │ Check: Code Quality, Requirements Match, Data Validity
    ├─ APPROVED ──▶ Execute ──▶ Results
    ├─ DATA ISSUE ──▶ Retry (up to max_retries)
    ├─ UI CHANGE ──▶ Stop & Report (manual fix needed)
    └─ MISMATCH ──▶ Stop & Report
```

## 🛠 Configuration Options

Edit `config/settings.py` or `.env`:

```python
# OpenAI
OPENAI_MODEL = "gpt-4-turbo-preview"  # or gpt-3.5-turbo
OPENAI_TEMPERATURE = 0.7  # 0-1, lower = more deterministic

# Execution
HEADLESS = True  # Run browser in headless mode
IMPLICIT_WAIT = 10  # Seconds for element waits
SCREENSHOT_ON_FAILURE = True  # Capture screenshots

# Retry
MAX_RETRY_LOOPS = 3  # Max retry attempts
```

## 📂 Project Structure

```
qa_testing_agent/
├── agents/                 # AI agents
│   ├── requirements_agent.py
│   ├── test_designer_agent.py
│   └── reviewer_agent.py
├── parsers/                # Input parsers
│   └── excel_parser.py
├── generators/             # Code/data generators
│   └── mock_data_generator.py
├── executors/              # Test execution
│   └── test_executor.py
├── utils/                  # Utilities
│   └── report_generator.py
├── config/                 # Configuration
│   └── settings.py
├── test_inputs/            # Input test cases
├── reports/                # Generated reports
├── models.py              # Data models
├── orchestrator.py        # Main orchestrator
├── main.py               # Entry point
├── requirements.txt      # Dependencies
├── .env.example         # Environment template
└── README.md            # This file
```

## 🔍 Logging

Logs are written to:
- **Console**: Real-time output
- **File**: `qa_agent.log` for detailed review

Log levels:
- `INFO`: Process steps and summaries
- `WARNING`: Non-critical issues
- `ERROR`: Critical failures

## 💾 Generated Output

### Reports Directory
```
reports/
├── qa_suite_YYYYMMDD_HHMMSS_report.html  # Main report
├── screenshots/                          # Failure screenshots
└── test_execution/
    ├── test_*.py              # Generated test files
    └── report_*.html          # Individual test reports
```

## 🎓 Example Usage

```python
from main import QATestingPipeline
from config.settings import settings

# Initialize pipeline
pipeline = QATestingPipeline()

# Run complete workflow
report_path = pipeline.run()

# Access report
print(f"Report generated at: {report_path}")
```

## 🐛 Troubleshooting

### "OPENAI_API_KEY not set"
- Add `OPENAI_API_KEY` to `.env` file
- Or set environment variable: `export OPENAI_API_KEY=your_key`

### "No test cases found"
- Ensure test_inputs folder exists
- Check Excel files are in correct format
- Verify column headers match expected names

### Tests executing but failing
- Check screenshot in report for UI issues
- Review execution logs for error messages
- Verify test data generation in report
- Check app/environment is accessible

### JSON parsing errors
- May indicate LLM response format issue
- Verify OpenAI API quota and rate limits
- Check model availability
- Review LLM prompt construction

## 🚦 Best Practices

1. **Test Case Design**
   - Clear step descriptions
   - Specific expected results
   - Include both positive and negative cases

2. **Data Management**
   - Let system generate mock data
   - Specify data requirements in Excel
   - Review generated data in reports

3. **Report Review**
   - Check rejection reasons carefully
   - Review failed test screenshots
   - Examine execution logs for patterns

4. **CI/CD Integration**
   - Run as scheduled test job
   - Parse HTML report for metrics
   - Archive reports for history

## 📈 Metrics & Analytics

The report includes:
- **Pass Rate**: % of tests passed
- **Approval Rate**: % of tests approved by reviewer
- **Test Duration**: Individual and total
- **Coverage**: Tests per scenario

## 🔐 Security Considerations

- Store `.env` securely (don't commit to git)
- Limit OpenAI API key access
- Use headless mode in production
- Sanitize sensitive data from logs

## 🤝 Contributing

Improvements welcome! Areas for enhancement:
- Support for additional UI frameworks
- API testing capabilities
- Performance testing integration
- Dashboard for metrics
- Slack/Teams integration

## 📄 License

[Your License Here]

## 📞 Support

- Check logs: `qa_agent.log`
- Review generated reports in `reports/` folder
- Examine HTML reports for detailed error info

---

**Built with OpenAI, Selenium, Playwright, and Python** 🚀
