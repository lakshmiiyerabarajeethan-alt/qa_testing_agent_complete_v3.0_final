# 🧠 QA Testing Agent v3.0

An AI-powered end-to-end testing agent that automates the test lifecycle — from **user story analysis** to **test case generation**, **execution**, and **reporting**.

## Overview

This project explores the use of Large Language Models (LLMs) to transform how QA teams approach test case development. The agent ingests user stories or requirements, automatically generates comprehensive test cases (positive, negative, edge cases, and boundary scenarios), and can execute them against a target application.

### What It Does

1. **Requirement Analysis** — Parses user stories/requirements to understand acceptance criteria and business logic
2. **Test Case Generation** — Uses AI (Claude/GPT) to generate structured test cases with:
   - Happy path scenarios
   - Negative test cases
   - Edge cases and boundary values
   - Test data suggestions
3. **Test Execution** — Orchestrates automated test execution using Playwright
4. **Reporting** — Generates execution reports with pass/fail status and coverage metrics
5. **Human Override** — Supports manual review and modification of AI-generated test cases before execution

## Architecture

```
┌─────────────────────┐
│   User Stories /     │
│   Requirements       │
└─────────┬───────────┘
          │
    ┌─────▼─────┐
    │   AI/LLM   │  ← Analyzes requirements
    │   Engine    │  ← Generates test cases
    └─────┬─────┘
          │
    ┌─────▼──────────┐
    │  Human Review   │  ← Optional validation
    │  & Override     │
    └─────┬──────────┘
          │
    ┌─────▼─────┐
    │  Playwright │  ← Executes tests
    │  Runner     │
    └─────┬─────┘
          │
    ┌─────▼──────┐
    │  Reports &  │  ← Results + coverage
    │  Metrics    │
    └────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI/LLM | Claude API / OpenAI GPT |
| Test Execution | Playwright (Python) |
| Language | Python 3.10+ |
| Orchestration | Custom Python pipeline |

## Why This Matters

- **Speed** — Generates test cases in minutes instead of hours
- **Coverage** — AI identifies edge cases that manual analysis often misses
- **Consistency** — Standardized test case format across the team
- **Traceability** — Each generated test maps back to its source requirement
- **Human-in-the-loop** — AI suggests, humans validate — best of both worlds

## Status

This is a working prototype / proof of concept demonstrating AI-augmented QA workflows. It represents my exploration of how AI can enhance — not replace — the testing process.

## Author

**Lakshmi Iyer** — QA Engineer exploring the intersection of AI and software testing.
