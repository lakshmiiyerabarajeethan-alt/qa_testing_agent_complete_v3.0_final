"""
Test Case Generator Agent
Generates test cases from user stories using OpenAI
Supports stories from CSV, Azure DevOps, Jira, Linear, or any source
"""
import json
import logging
import re
from typing import List, Union
from openai import OpenAI
from models import TestCase, TestStep
from config.settings import settings, TestStatus
from connectors.azure_devops_connector import AzureDevOpsStory

logger = logging.getLogger(__name__)

class TestCaseGeneratorAgent:
    """
    Generates test cases from user stories
    Works with any story format that has:
    - title: str
    - description: str
    - acceptance_criteria: List[str]
    - (optional) priority, state, assignee, tags, story_points
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def _ensure_story_id(self, story, idx: int = None) -> None:
        """
        Ensure the story has an id attribute for downstream logging and metadata.
        For CSV or generic stories that lack an id, create a stable fallback.
        """
        if getattr(story, "id", None):
            return

        if idx is not None:
            fallback_id = f"CSV-{idx}"
        elif getattr(story, "title", None):
            fallback_id = f"CSV-{abs(hash(story.title)) % 100000}"
        else:
            fallback_id = "CSV-UNKNOWN"

        try:
            story.id = fallback_id
        except Exception:
            # If the story object is immutable, we just skip setting it.
            pass
    
    def generate_test_cases_from_story(self, story) -> List[TestCase]:
        """
        Generate test cases from a user story
        
        Args:
            story: Story object (CSVStory, AzureDevOpsStory, or any object with story attributes)
            
        Returns:
            List of TestCase objects
        """
        self._ensure_story_id(story)
        logger.info(f"Generating test cases from story: {story.title}")
        
        prompt = self._build_prompt(story)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert QA analyst specializing in test case generation from user stories.
                        Generate comprehensive, well-structured test cases that cover:
                        1. Main functionality (happy path)
                        2. Edge cases
                        3. Error scenarios
                        4. User interactions
                        
                        Always respond with valid JSON only."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=3000
            )
            
            result_text = response.choices[0].message.content or ""
            result_json = self._safe_parse_json(result_text)
            if result_json is None:
                logger.error("Failed to parse JSON response: empty or invalid content")
                logger.debug(f"Raw model response (first 500 chars): {result_text[:500]}")
                return self._create_default_test_case(story)
            
            test_cases = self._parse_test_cases(result_json, story)
            
            logger.info(f"Generated {len(test_cases)} test cases from story: {story.title}")
            return test_cases
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.debug(f"Raw model response (first 500 chars): {result_text[:500]}")
            return self._create_default_test_case(story)
        except Exception as e:
            logger.error(f"Error generating test cases: {str(e)}")
            raise
    
    def generate_test_cases_from_stories(self, stories: List) -> List[TestCase]:
        """
        Generate test cases from multiple user stories
        
        Args:
            stories: List of story objects (CSVStory, AzureDevOpsStory, etc.)
            
        Returns:
            List of TestCase objects
        """
        all_test_cases = []
        
        for idx, story in enumerate(stories, 1):
            self._ensure_story_id(story, idx=idx)
            logger.info(f"\n[{idx}/{len(stories)}] Processing story: {story.title}")
            
            try:
                test_cases = self.generate_test_cases_from_story(story)
                all_test_cases.extend(test_cases)
            except Exception as e:
                logger.error(f"Failed to generate test cases for story {story.id}: {str(e)}")
                # Add default test case
                default_case = self._create_default_test_case(story)
                all_test_cases.extend(default_case)
        
        logger.info(f"\nTotal test cases generated: {len(all_test_cases)}")
        return all_test_cases
    
    def _build_prompt(self, story: AzureDevOpsStory) -> str:
        """Build the prompt for test case generation"""
        acceptance_criteria_text = "\n".join([
            f"  - {criterion}" for criterion in story.acceptance_criteria
        ]) if story.acceptance_criteria else "  - Execute the user story functionality"
        
        prompt = f"""Generate test cases for the following Azure DevOps user story:

STORY TITLE: {story.title}
STORY ID: {story.id}
PRIORITY: {story.priority}

DESCRIPTION:
{story.description if story.description else "No detailed description provided"}

ACCEPTANCE CRITERIA:
{acceptance_criteria_text}

TAGS: {', '.join(story.tags) if story.tags else 'None'}

Please generate comprehensive test cases that:
1. Cover all acceptance criteria
2. Include happy path and edge cases
3. Test error conditions
4. Validate user interactions
5. Check data validation
6. Include categories: Functional, Data Integrity, Permissions/Security, Boundary/Volume,
   Error Handling, Performance, UX/Accessibility

Return ONLY a JSON array with the following structure:
[
  {{
    "scenario": "Scenario name (e.g., 'Happy Path Login')",
    "case_name": "test_case_name_unique_identifier",
    "description": "Brief description of what this test case covers",
    "steps": [
      {{
        "step_no": 1,
        "description": "Clear step description",
        "expected_result": "What should happen"
      }},
      {{
        "step_no": 2,
        "description": "Next step",
        "expected_result": "Expected outcome"
      }}
    ]
  }},
  {{
    "scenario": "Edge Case Scenario",
    "case_name": "test_case_edge_case_identifier",
    "description": "Edge case testing",
    "steps": [...]
  }}
]

Generate AT LEAST 3 test cases (happy path + edge cases + error scenario).
Each test case should have 3-8 steps minimum.
"""
        return prompt

    def _safe_parse_json(self, text: str):
        """
        Attempt to parse a JSON array from model output.
        Accepts raw JSON or JSON wrapped in code fences/text.
        """
        if not text:
            return None

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()

        # Direct parse attempt
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Extract first JSON array from the response
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return None

        snippet = cleaned[start:end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None
    
    def _parse_test_cases(self, json_data: list, story: AzureDevOpsStory) -> List[TestCase]:
        """
        Parse generated JSON into TestCase objects
        
        Args:
            json_data: List of test case dictionaries
            story: Original story (for metadata)
            
        Returns:
            List of TestCase objects
        """
        test_cases = []
        
        for test_data in json_data:
            try:
                steps = []
                for step_data in test_data.get("steps", []):
                    step = TestStep(
                        step_no=step_data.get("step_no", len(steps) + 1),
                        description=step_data.get("description", ""),
                        expected_results=step_data.get("expected_result", ""),
                        status=TestStatus.PENDING
                    )
                    steps.append(step)
                
                if not steps:
                    logger.warning(f"No steps generated for test case: {test_data.get('case_name')}")
                    continue
                
                test_case = TestCase(
                    test_scenario=test_data.get("scenario", "Unknown Scenario"),
                    test_case_name=test_data.get("case_name", "unknown_test"),
                    test_data={"story_id": story.id, "story_title": story.title},
                    steps=steps,
                    remarks=f"Generated from Azure DevOps story: {story.title}"
                )
                
                test_cases.append(test_case)
                
            except Exception as e:
                logger.error(f"Error parsing test case: {str(e)}")
                continue
        
        return test_cases
    
    def _create_default_test_case(self, story) -> List[TestCase]:
        """
        Create a default test case if generation fails
        
        Args:
            story: Story object
            
        Returns:
            List with single default TestCase
        """
        logger.warning(f"Creating default test case for story: {story.title}")
        
        scenario_name = story.title.split()[0] if story.title else "Default"
        case_name = f"test_{story.id}_default".replace(" ", "_").lower()
        
        steps = []
        
        # Default step 1: Navigate/access
        steps.append(TestStep(
            step_no=1,
            description=f"Navigate to {scenario_name} feature",
            expected_results="Feature is accessible",
            status=TestStatus.PENDING
        ))
        
        # Add steps from acceptance criteria
        for idx, criterion in enumerate(story.acceptance_criteria[:3], 2):
            steps.append(TestStep(
                step_no=idx,
                description=f"Execute: {criterion}",
                expected_results=criterion,
                status=TestStatus.PENDING
            ))
        
        # If no criteria, add a generic step
        if len(steps) == 1:
            steps.append(TestStep(
                step_no=2,
                description="Verify functionality works as expected",
                expected_results="Feature functions correctly",
                status=TestStatus.PENDING
            ))
        
        test_case = TestCase(
            test_scenario=scenario_name,
            test_case_name=case_name,
            test_data={"story_id": story.id, "story_title": story.title},
            steps=steps,
            remarks=f"Default test case for Azure DevOps story: {story.title}"
        )
        
        return [test_case]
    
    def validate_test_cases(self, test_cases: List[TestCase]) -> bool:
        """
        Validate generated test cases
        
        Args:
            test_cases: List of TestCase objects
            
        Returns:
            True if all valid, False otherwise
        """
        if not test_cases:
            logger.warning("No test cases to validate")
            return False
        
        issues = []
        
        for idx, test_case in enumerate(test_cases):
            if not test_case.test_scenario:
                issues.append(f"Test {idx}: Missing scenario")
            if not test_case.test_case_name:
                issues.append(f"Test {idx}: Missing case name")
            if not test_case.steps or len(test_case.steps) == 0:
                issues.append(f"Test {idx}: No steps defined")
            else:
                for step in test_case.steps:
                    if not step.description:
                        issues.append(f"Test {idx}: Step {step.step_no} missing description")
                    if not step.expected_results:
                        issues.append(f"Test {idx}: Step {step.step_no} missing expected results")
        
        if issues:
            for issue in issues:
                logger.warning(f"Validation issue: {issue}")
            return False
        
        logger.info(f"All {len(test_cases)} test cases validated successfully")
        return True
