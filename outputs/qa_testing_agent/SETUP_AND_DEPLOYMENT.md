# QA Testing Agent - Setup & Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Testing & Validation](#testing--validation)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **Python**: 3.9 or higher
- **OS**: Linux, macOS, or Windows
- **RAM**: 4GB minimum
- **Disk**: 2GB free space for reports and dependencies

### External Requirements
- **OpenAI API Key**: Get from https://platform.openai.com/api-keys
- **Web Drivers**: Chrome/Firefox for Selenium, or Playwright drivers

### API Account Setup
1. Sign up for OpenAI API: https://platform.openai.com
2. Create API key in settings
3. Set up billing and usage limits
4. Note your API key for configuration

---

## Installation

### Step 1: Clone/Setup Project

```bash
# Navigate to project location
cd qa_testing_agent

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Install Playwright browsers (if using Playwright)
playwright install

# Or for Selenium, download ChromeDriver:
# https://chromedriver.chromium.org/
```

### Step 3: Setup Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
nano .env  # or use your preferred editor
```

**Required .env variables:**
```
OPENAI_API_KEY=sk-...your-key...
OPENAI_MODEL=gpt-4-turbo-preview
```

### Step 4: Verify Installation

```bash
# Check Python version
python --version  # Should be 3.9+

# Test imports
python -c "import openai; print('OpenAI SDK loaded')"
python -c "import selenium; print('Selenium loaded')"
python -c "import pytest; print('Pytest loaded')"

# Verify directory structure
ls -la  # Check all folders exist
```

---

## Configuration

### Environment Variables (.env)

```ini
# ========== OPENAI CONFIG ==========
OPENAI_API_KEY=sk-...your-api-key...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000

# ========== PROJECT PATHS ==========
PROJECT_NAME=QA Testing Agent
TEST_INPUT_FOLDER=./test_inputs
REPORT_OUTPUT_FOLDER=./reports
SCREENSHOTS_FOLDER=./reports/screenshots

# ========== BROWSER CONFIG ==========
BROWSER_TYPE=chrome              # Options: chrome, firefox, webkit
HEADLESS=false                  # Set to true for CI/CD
SCREENSHOT_ON_FAILURE=true
IMPLICIT_WAIT=10

# ========== AGENT CONFIG ==========
MAX_RETRY_LOOPS=3
INCLUDE_MOCK_DATA_GENERATION=true
PARALLEL_EXECUTION=false
```

### Python Configuration (config/settings.py)

Modify for your environment:

```python
# In config/settings.py:
settings.OPENAI_MODEL = "gpt-4-turbo-preview"  # vs gpt-3.5-turbo for cost savings
settings.HEADLESS = True  # For CI/CD pipelines
settings.SCREENSHOT_ON_FAILURE = True  # Recommended for debugging
settings.MAX_RETRY_LOOPS = 3  # Max attempts for data-issue retries
```

---

## Testing & Validation

### Step 1: Verify API Connectivity

```bash
# Test OpenAI connection
python -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.chat.completions.create(
    model='gpt-3.5-turbo',
    messages=[{'role': 'user', 'content': 'Say hello'}]
)
print('API Connection: OK')
print(response.choices[0].message.content)
"
```

### Step 2: Test Excel Parser

```bash
# Create test_inputs folder with sample Excel file
mkdir -p test_inputs
cp ../Metsa_Version_upgrade_DEV.xlsx test_inputs/

# Test parsing
python -c "
from parsers.excel_parser import TestCaseParser
parser = TestCaseParser('./test_inputs')
test_cases = parser.parse_folder()
print(f'Parsed {len(test_cases)} test cases')
for tc in test_cases[:2]:
    print(f'  - {tc.test_case_name}: {len(tc.steps)} steps')
"
```

### Step 3: Test Agents

```bash
# Run examples to verify agents work
python examples.py

# Expected output:
# - Test case creation
# - Mock data generation
# - Agent workflow documentation
```

### Step 4: Full Pipeline Validation

```bash
# Create small test with 1-2 test cases
# Place in test_inputs/

# Run full pipeline
python main.py

# Check output:
# - logs: qa_agent.log
# - reports: ./reports/qa_suite_*.html
```

---

## Deployment

### Development Deployment

```bash
# Create isolated project directory
mkdir -p /opt/qa-agent
cd /opt/qa-agent

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install project
pip install -r requirements.txt
playwright install

# Configure
cp .env.example .env
nano .env  # Set OPENAI_API_KEY and other config

# Test
python main.py
```

### Production Deployment

#### Docker Deployment (Recommended)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directories
RUN mkdir -p test_inputs reports

# Set environment
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

# Run on container start
CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t qa-testing-agent:latest .
docker run --env-file .env -v $(pwd)/test_inputs:/app/test_inputs -v $(pwd)/reports:/app/reports qa-testing-agent:latest
```

#### CI/CD Integration (GitHub Actions)

```yaml
# .github/workflows/qa-tests.yml
name: QA Testing Agent

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

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
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        playwright install
    
    - name: Run QA Tests
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        HEADLESS: true
      run: |
        python main.py
    
    - name: Upload report
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: qa-reports
        path: reports/
        retention-days: 30
    
    - name: Slack Notification
      if: always()
      uses: slackapi/slack-github-action@v1
      with:
        webhook-url: ${{ secrets.SLACK_WEBHOOK }}
```

#### Jenkins Integration

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
        HEADLESS = 'true'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    source venv/bin/activate
                    pip install -r requirements.txt
                    playwright install
                '''
            }
        }
        
        stage('Run Tests') {
            steps {
                sh 'source venv/bin/activate && python main.py'
            }
        }
        
        stage('Archive Reports') {
            steps {
                archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'reports',
                    reportFiles: '*.html',
                    reportName: 'QA Test Report'
                ])
            }
        }
    }
    
    post {
        always {
            junit testResults: 'reports/*.xml', allowEmptyResults: true
        }
        failure {
            // Send notification
            echo 'Tests failed - notifying team'
        }
    }
}
```

### Cloud Deployment (AWS)

```bash
# AWS Lambda function (example)
# Create zip with dependencies
pip install -r requirements.txt -t package/
cd package
zip -r ../function.zip .
cd ..
zip function.zip main.py models.py orchestrator.py ...

# Deploy
aws lambda create-function \
    --function-name qa-testing-agent \
    --runtime python3.11 \
    --role arn:aws:iam::ACCOUNT:role/lambda-role \
    --handler main.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 300 \
    --environment Variables={OPENAI_API_KEY=sk-...}

# Trigger from S3 or EventBridge
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'openai'"

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate  # On Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "OPENAI_API_KEY not found"

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify key is set
echo $OPENAI_API_KEY

# If not, set it:
export OPENAI_API_KEY="sk-..."

# Or add to .env:
nano .env
# OPENAI_API_KEY=sk-...
```

### Issue: "No test cases found"

**Solution:**
```bash
# Check test_inputs folder
ls -la test_inputs/

# Verify Excel format
python -c "
from openpyxl import load_workbook
wb = load_workbook('test_inputs/your_file.xlsx')
ws = wb.active
for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
    print(row)
"

# Expected headers:
# Test Scenario | Test Case | Test Data | Step No. | ...
```

### Issue: "Browser not found" (Selenium)

**Solution:**
```bash
# Install Playwright browsers
playwright install

# Or download Selenium ChromeDriver
# https://chromedriver.chromium.org/
# Place in PATH or specify in code
```

### Issue: "API rate limit exceeded"

**Solution:**
- Reduce concurrent requests
- Add delays between requests
- Upgrade OpenAI plan
- Use gpt-3.5-turbo instead of gpt-4

### Issue: "Test execution timeout"

**Solution:**
```python
# In config/settings.py:
settings.IMPLICIT_WAIT = 15  # Increase from 10
settings.HEADLESS = True     # Might be faster

# Or in orchestrator.py:
# executor = TestExecutor()
# result.timeout_seconds = 600  # Increase timeout
```

---

## Performance Optimization

### For Large Test Suites

```python
# config/settings.py
settings.PARALLEL_EXECUTION = True  # Enable parallel execution
settings.MAX_RETRY_LOOPS = 2  # Reduce retry attempts

# Use gpt-3.5-turbo instead of gpt-4
settings.OPENAI_MODEL = "gpt-3.5-turbo"

# Batch process test cases
# Process in chunks instead of all at once
```

### For Cost Reduction

```python
# Use gpt-3.5-turbo (10x cheaper than gpt-4)
OPENAI_MODEL = "gpt-3.5-turbo"

# Lower temperature for more deterministic results
OPENAI_TEMPERATURE = 0.3

# Reduce max tokens
OPENAI_MAX_TOKENS = 1500
```

---

## Monitoring & Maintenance

### Log Analysis

```bash
# Watch logs in real-time
tail -f qa_agent.log

# Search for errors
grep ERROR qa_agent.log

# Count test results
grep "PASSED\|FAILED" qa_agent.log | wc -l
```

### Report Analysis

```bash
# Generate metrics from reports
python -c "
import json
from pathlib import Path

reports_dir = Path('reports')
for html_file in reports_dir.glob('*.html'):
    print(f'Report: {html_file.name}')
    # Parse metrics from HTML
"
```

### Database Logging (Optional)

```python
# Log results to database
import sqlite3

def log_test_result(test_id, status, duration):
    conn = sqlite3.connect('qa_results.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO test_results 
        (test_id, status, duration, timestamp)
        VALUES (?, ?, ?, datetime('now'))
    ''', (test_id, status, duration))
    conn.commit()
```

---

## Support & Help

For issues or questions:
1. Check logs: `qa_agent.log`
2. Review examples: `python examples.py`
3. Check API status: https://status.openai.com
4. Verify configuration: `grep -E "OPENAI|TEST_INPUT" .env`

---

**Last Updated**: 2024
