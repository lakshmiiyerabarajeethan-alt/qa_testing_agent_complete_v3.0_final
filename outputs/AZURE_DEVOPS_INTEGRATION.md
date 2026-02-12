# Azure DevOps Integration Guide

Complete guide to integrating Azure DevOps with the QA Testing Agent for automated test case generation and execution.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup Instructions](#setup-instructions)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [API Reference](#api-reference)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What It Does

The Azure DevOps integration enables a complete end-to-end automation workflow:

```
Azure DevOps User Stories
    ↓
Fetch Stories & Requirements
    ↓
AI-Generated Test Cases (from stories)
    ↓
Save to Excel Format
    ↓
Multi-Agent Analysis & Design
    ↓
Automated Test Execution
    ↓
Comprehensive HTML Report
```

### Key Features

✅ **Automated Test Case Generation** from user stories
✅ **Story-Based Context** - Tests understand business requirements
✅ **Acceptance Criteria Mapping** - Tests cover all acceptance criteria
✅ **Excel Output** - Generated test cases saved in standardformat
✅ **Full Integration** - Seamlessly integrates with existing pipeline
✅ **Status Updates** - Can update work item status after testing
✅ **Test Results Comments** - Add test results as comments to stories

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────┐
│   Azure DevOps Organization     │
│                                 │
│  ┌──────────────────────────┐  │
│  │   User Stories (Work     │  │
│  │   Items - Type: Story)   │  │
│  │                          │  │
│  │  - Title                 │  │
│  │  - Description           │  │
│  │  - Acceptance Criteria   │  │
│  │  - Area Path             │  │
│  │  - Iteration Path        │  │
│  │  - Priority              │  │
│  │  - Tags                  │  │
│  └──────────────────────────┘  │
└──────────────┬──────────────────┘
               │
               │ REST API
               │ (PAT Authentication)
               ▼
┌──────────────────────────────────────┐
│  QA Testing Agent                    │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ AzureDevOpsConnector           │ │
│  │ (connectors/)                  │ │
│  │                                │ │
│  │ - test_connection()            │ │
│  │ - get_user_stories()           │ │
│  │ - get_story_by_id()            │ │
│  │ - update_story_status()        │ │
│  │ - add_test_results_comment()   │ │
│  └────────────────┬───────────────┘ │
│                   │                  │
│  ┌────────────────▼───────────────┐ │
│  │ TestCaseGeneratorAgent         │ │
│  │ (agents/)                      │ │
│  │                                │ │
│  │ - generate_test_cases_from_    │ │
│  │   story()                      │ │
│  │ - generate_test_cases_from_    │ │
│  │   stories()                    │ │
│  │ - validate_test_cases()        │ │
│  └────────────────┬───────────────┘ │
│                   │                  │
│  ┌────────────────▼───────────────┐ │
│  │ ExcelWriter (utils/)           │ │
│  │                                │ │
│  │ - write_test_cases()           │ │
│  │ - append_test_cases()          │ │
│  │ - create_template()            │ │
│  └────────────────┬───────────────┘ │
│                   │                  │
│  ┌────────────────▼───────────────┐ │
│  │ Existing Pipeline              │ │
│  │ (orchestrator, executor,       │ │
│  │  report_generator)             │ │
│  └────────────────────────────────┘ │
└──────────────────────────────────────┘
               │
               ▼
         HTML Report
       (with metrics & results)
```

### Data Flow

```
1. FETCH PHASE
   Azure DevOps REST API
      ↓ (WIQL Query)
   List of Work Items
      ↓
   Get Detailed Info (per item)
      ↓
   AzureDevOpsStory Objects

2. GENERATION PHASE
   AzureDevOpsStory
      ↓ (OpenAI GPT-4)
   Generated Test Cases
      ↓
   Validation
      ↓
   Excel File (.xlsx)

3. EXECUTION PHASE
   Excel File
      ↓ (Parse)
   TestCase Objects
      ↓ (Normal Pipeline)
   HTML Report

4. UPDATE PHASE (Optional)
   Test Results
      ↓ (Update Story Status)
   Azure DevOps Work Item
      ↓
   Add Comment
      ↓
   Story Status Updated
```

---

## Setup Instructions

### Prerequisites

- Azure DevOps account with project
- Personal Access Token (PAT) from Azure DevOps
- Python 3.9+
- OpenAI API key

### Step 1: Create Personal Access Token (PAT)

1. Go to Azure DevOps: https://dev.azure.com
2. Click on **User Settings** (top right corner)
3. Select **Personal access tokens**
4. Click **New Token**
5. Configure:
   - **Name**: `QA-Testing-Agent`
   - **Organization**: Select your organization
   - **Expiration**: Set appropriate expiration (e.g., 1 year)
   - **Scopes**: Select the following:
     - ✓ Work Items (Read)
     - ✓ Work Items (Write)
6. Click **Create**
7. **Copy the token** (you won't see it again!)

### Step 2: Get Organization and Project Names

```
https://dev.azure.com/{organization}/{project}

Example:
https://dev.azure.com/mycompany/myproject

organization = "mycompany"
project = "myproject"
```

### Step 3: Install Additional Dependencies

```bash
cd qa_testing_agent

# If using Azure DevOps integration, requests is already included
pip install -r requirements.txt
```

### Step 4: Verify Connection

```bash
python -c "
from connectors.azure_devops_connector import AzureDevOpsConnector
from config.settings import settings

connector = AzureDevOpsConnector(
    organization='your-org',
    project='your-project',
    pat_token='your-pat-token'
)

if connector.test_connection():
    print('✓ Connection successful!')
else:
    print('✗ Connection failed')
"
```

---

## Configuration

### Environment Variables

Add to `.env` file:

```ini
# Existing config
OPENAI_API_KEY=sk-...

# Optional Azure DevOps defaults
AZURE_DEVOPS_ORG=myorganization
AZURE_DEVOPS_PROJECT=myproject
AZURE_DEVOPS_PAT=...token...
```

### Settings in Code

Modify `config/settings.py` if needed:

```python
# Connector settings
AZURE_DEVOPS_ORG = os.getenv("AZURE_DEVOPS_ORG", "")
AZURE_DEVOPS_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT", "")
AZURE_DEVOPS_PAT = os.getenv("AZURE_DEVOPS_PAT", "")

# Test case generation
MIN_STEPS_PER_TEST = 3
MAX_STEPS_PER_TEST = 8
```

---

## Usage

### Option 1: Interactive Mode (Recommended)

Run the system and select Azure DevOps option:

```bash
cd qa_testing_agent
python main.py

# Output:
# QA TESTING AGENT
# ===============================================
# 1. Azure DevOps (fetch stories and generate tests)
# 2. Excel Files (manual test cases)
# 3. Create Excel Template
#
# Select option (1-3): 1
#
# AZURE DEVOPS CONFIGURATION
# ===============================================
# Organization: mycompany
# Project: myproject
# PAT Token: ••••••••••••••••••••••••••••••••••••
# Area Path (optional): MyApp\Features
```

### Option 2: Programmatic Usage

```python
from main import QATestingPipeline

pipeline = QATestingPipeline()

report_path = pipeline.run_from_azure_devops(
    organization="mycompany",
    project="myproject",
    pat_token="your-pat-token",
    area_path="MyApp\\Features",
    iteration_path="Sprint 1"
)

print(f"Report: {report_path}")
```

### Option 3: Command Line with Environment Variables

```bash
# Set environment variables
export AZURE_DEVOPS_ORG=mycompany
export AZURE_DEVOPS_PROJECT=myproject
export AZURE_DEVOPS_PAT=your-pat-token
export OPENAI_API_KEY=sk-...

# Run
python main.py
```

---

## API Reference

### AzureDevOpsConnector

#### Constructor

```python
connector = AzureDevOpsConnector(
    organization="mycompany",
    project="myproject",
    pat_token="your-pat-token"
)
```

#### Methods

##### `test_connection() → bool`

Test connection to Azure DevOps

```python
if connector.test_connection():
    print("Connected!")
```

##### `get_user_stories() → List[AzureDevOpsStory]`

Fetch user stories with optional filters

```python
stories = connector.get_user_stories(
    area_path="MyApp\\Features",
    iteration_path="Sprint 1",
    state="Active",
    top=100
)

for story in stories:
    print(f"Story {story.id}: {story.title}")
```

##### `get_story_by_id(story_id) → AzureDevOpsStory`

Get specific story by ID

```python
story = connector.get_story_by_id(12345)
print(story.title)
print(story.acceptance_criteria)
```

##### `get_story_by_area(area_path) → List[AzureDevOpsStory]`

Get all stories in an area

```python
stories = connector.get_story_by_area("MyApp\\Features")
```

##### `get_story_by_iteration(iteration_path) → List[AzureDevOpsStory]`

Get stories in a sprint/iteration

```python
stories = connector.get_story_by_iteration("Sprint 1")
```

##### `update_story_status(story_id, new_state) → bool`

Update story status after testing

```python
success = connector.update_story_status(12345, "Tested")
```

States: `"New"`, `"Active"`, `"Resolved"`, `"Closed"`, `"Testing"`, `"Tested"`

##### `add_test_results_comment(story_id, test_results) → bool`

Add test results as comment to story

```python
results = "Tests: 5 passed, 1 failed. Pass rate: 83.3%"
success = connector.add_test_results_comment(12345, results)
```

### TestCaseGeneratorAgent

#### Methods

##### `generate_test_cases_from_story(story) → List[TestCase]`

Generate test cases from a single story

```python
generator = TestCaseGeneratorAgent()
test_cases = generator.generate_test_cases_from_story(story)
```

##### `generate_test_cases_from_stories(stories) → List[TestCase]`

Generate test cases from multiple stories

```python
stories = connector.get_user_stories()
test_cases = generator.generate_test_cases_from_stories(stories)
```

##### `validate_test_cases(test_cases) → bool`

Validate generated test cases

```python
if generator.validate_test_cases(test_cases):
    print("All test cases are valid")
```

### ExcelWriter

#### Methods

##### `write_test_cases(test_cases, filename) → str`

Write test cases to Excel file

```python
writer = ExcelWriter("./test_inputs")
path = writer.write_test_cases(test_cases, "my_tests.xlsx")
```

##### `append_test_cases(filepath, new_test_cases) → str`

Append test cases to existing Excel file

```python
writer.append_test_cases("./test_inputs/existing.xlsx", new_cases)
```

##### `create_template(filename) → str`

Create empty template Excel file

```python
template_path = writer.create_template("template.xlsx")
```

---

## Examples

### Complete Flow Example

```python
from connectors.azure_devops_connector import AzureDevOpsConnector
from agents.test_case_generator_agent import TestCaseGeneratorAgent
from utils.excel_writer import ExcelWriter
from main import QATestingPipeline

# Step 1: Connect to Azure DevOps
connector = AzureDevOpsConnector(
    organization="mycompany",
    project="myproject",
    pat_token="your-pat-token"
)

# Test connection
assert connector.test_connection(), "Connection failed"

# Step 2: Fetch user stories
stories = connector.get_user_stories(
    area_path="MyApp\\Features",
    state="Active"
)
print(f"Fetched {len(stories)} stories")

# Step 3: Generate test cases
generator = TestCaseGeneratorAgent()
test_cases = generator.generate_test_cases_from_stories(stories)
print(f"Generated {len(test_cases)} test cases")

# Step 4: Validate test cases
assert generator.validate_test_cases(test_cases), "Validation failed"

# Step 5: Save to Excel
writer = ExcelWriter("./test_inputs")
excel_path = writer.write_test_cases(test_cases, "generated_tests.xlsx")
print(f"Saved to {excel_path}")

# Step 6: Run full pipeline
pipeline = QATestingPipeline()
report_path = pipeline.run_from_azure_devops(
    organization="mycompany",
    project="myproject",
    pat_token="your-pat-token",
    area_path="MyApp\\Features"
)

print(f"Report: {report_path}")

# Step 7: Update story statuses (optional)
for story in stories:
    connector.update_story_status(int(story.id), "Tested")
    connector.add_test_results_comment(int(story.id), 
        "Automated tests generated and executed successfully")
```

### Filtering Examples

```python
# Get stories from specific area
stories = connector.get_user_stories(area_path="MyApp\\UI\\Login")

# Get stories from specific sprint
stories = connector.get_user_stories(iteration_path="Sprint 5")

# Get only active stories
stories = connector.get_user_stories(state="Active")

# Get stories from specific area AND sprint
stories = connector.get_user_stories(
    area_path="MyApp\\Features",
    iteration_path="Sprint 1",
    state="Active"
)

# Get many stories (up to 200)
all_stories = connector.get_user_stories(top=200)
```

---

## Troubleshooting

### Error: "Connection failed"

**Possible causes:**
- Invalid PAT token
- Wrong organization name
- Wrong project name
- Network connectivity issue

**Solution:**
```python
# Test each component
connector = AzureDevOpsConnector(org, project, token)
response = connector.session.get(f"{connector.base_url}/projects")
print(response.status_code)  # Should be 200
print(response.json())
```

### Error: "No user stories found"

**Possible causes:**
- No stories in specified area/iteration
- Stories in "Closed" state (filtered out by default)
- Wrong area/iteration path

**Solution:**
```python
# Check available work items
stories = connector.get_user_stories(state="Active", top=1)
if not stories:
    print("No active stories found")

# Try getting all states
stories = connector.get_user_stories()
print(f"Total stories: {len(stories)}")

# List areas
# (Manual: check in Azure DevOps web interface)
```

### Error: "Failed to parse JSON response"

**Possible causes:**
- OpenAI API rate limit
- Invalid response format
- Network timeout

**Solution:**
```python
# Check OpenAI status
# Add retry logic
from time import sleep

def generate_with_retry(generator, story, max_retries=3):
    for attempt in range(max_retries):
        try:
            return generator.generate_test_cases_from_story(story)
        except Exception as e:
            if attempt < max_retries - 1:
                sleep(5)  # Wait before retry
            else:
                raise

test_cases = generate_with_retry(generator, story)
```

### Error: "Excel file permission denied"

**Possible causes:**
- File is open in another program
- Insufficient permissions
- Read-only file

**Solution:**
```bash
# Close Excel file and retry
# Or use different filename
writer.write_test_cases(cases, "tests_new_timestamp.xlsx")
```

### Azure DevOps API Rate Limiting

Azure DevOps has rate limits. If you hit them:

```python
from time import sleep

stories = connector.get_user_stories(top=50)
for idx, story in enumerate(stories):
    if idx % 10 == 0:  # Every 10 stories
        sleep(5)  # Wait 5 seconds
    
    # Process story
    test_cases = generator.generate_test_cases_from_story(story)
```

---

## Advanced Configuration

### Custom Story Filtering

```python
# Get only high-priority stories
stories = connector.get_user_stories(state="Active")
high_priority = [s for s in stories if s.priority <= 2]
```

### Custom Test Case Generation

```python
# Generate different number of test cases per story
from agents.test_case_generator_agent import TestCaseGeneratorAgent

class CustomGenerator(TestCaseGeneratorAgent):
    def _build_prompt(self, story):
        # Customize prompt for specific requirements
        return super()._build_prompt(story) + \
            "\n\nGenerate at least 5 test cases including edge cases."

generator = CustomGenerator()
test_cases = generator.generate_test_cases_from_stories(stories)
```

### Batch Processing

```python
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d")

# Get stories from different iterations
for sprint in ["Sprint 1", "Sprint 2", "Sprint 3"]:
    stories = connector.get_user_stories(iteration_path=sprint)
    test_cases = generator.generate_test_cases_from_stories(stories)
    
    filename = f"tests_{sprint.replace(' ', '_')}_{timestamp}.xlsx"
    writer.write_test_cases(test_cases, filename)
    
    # Run pipeline
    pipeline.run_from_excel()
```

---

## Integration with CI/CD

### GitHub Actions

```yaml
name: Azure DevOps QA Tests

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday 2 AM

jobs:
  qa-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        playwright install
    
    - name: Run Azure DevOps QA Tests
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        AZURE_DEVOPS_ORG: ${{ secrets.AZURE_DEVOPS_ORG }}
        AZURE_DEVOPS_PROJECT: ${{ secrets.AZURE_DEVOPS_PROJECT }}
        AZURE_DEVOPS_PAT: ${{ secrets.AZURE_DEVOPS_PAT }}
      run: |
        python main.py
    
    - name: Upload Report
      uses: actions/upload-artifact@v3
      with:
        name: qa-report
        path: reports/
```

### Jenkins

```groovy
pipeline {
    agent any
    
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
        AZURE_DEVOPS_ORG = credentials('azure-devops-org')
        AZURE_DEVOPS_PROJECT = credentials('azure-devops-project')
        AZURE_DEVOPS_PAT = credentials('azure-devops-pat')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }
        
        stage('Generate and Execute Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    python main.py
                '''
            }
        }
        
        stage('Archive Results') {
            steps {
                archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            }
        }
    }
}
```

---

## Best Practices

1. **Use Acceptance Criteria** - Structure stories with clear acceptance criteria for better test generation
2. **Organize with Areas** - Use area paths to group related features
3. **Tag Stories** - Use tags for easy filtering and categorization
4. **Regular Runs** - Schedule weekly or bi-weekly test generation
5. **Update Stories** - Update story status after testing
6. **Monitor Reports** - Review generated reports for quality
7. **Version Control** - Store Excel files in source control
8. **Backup PAT** - Keep PAT tokens secure, rotate periodically

---

## Security Considerations

⚠️ **Important Security Notes:**

1. **Never commit PAT tokens** to version control
2. **Use environment variables** for sensitive data
3. **Rotate PAT tokens** regularly (set expiration)
4. **Limit PAT scope** to minimum required permissions
5. **Use CI/CD secrets** for deployment pipelines
6. **Audit logs** - Monitor who accessed the system
7. **Network security** - Use VPN for internal systems

Example `.env.template`:
```ini
# Example only - never commit actual values
OPENAI_API_KEY=YOUR_KEY_HERE
AZURE_DEVOPS_ORG=YOUR_ORG_HERE
AZURE_DEVOPS_PROJECT=YOUR_PROJECT_HERE
AZURE_DEVOPS_PAT=YOUR_PAT_HERE
```

---

**Azure DevOps Integration v1.0**  
**Last Updated**: February 2024
