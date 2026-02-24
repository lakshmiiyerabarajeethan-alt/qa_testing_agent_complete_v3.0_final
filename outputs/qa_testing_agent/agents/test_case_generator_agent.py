"""
Improved TestCaseGeneratorAgent
================================
Generates comprehensive test cases from user stories using OpenAI.

BUG FIX (v1.1):
  Root cause of "Failed to generate for story ?: '\\n    \"test_scenario\"'" error:

  In _call_llm(), self.SYSTEM_PROMPT.format(min_scenarios=..., max_scenarios=...)
  was called on a prompt that contained literal { } braces inside the JSON
  output-format example block.  Python's str.format() treats EVERY {word} as a
  named placeholder, so the brace pair surrounding "test_scenario" was read as
  a variable named '\\n    "test_scenario"' → KeyError.

  Fix: every literal { } in the JSON example is now written as {{ }} so
  str.format() passes them through unchanged.  The only real placeholders
  remaining are {min_scenarios} and {max_scenarios}.
"""

import json
import logging
from typing import List, Optional
from dataclasses import dataclass

from openai import OpenAI

from models import TestCase, TestStep
from config.settings import settings

logger = logging.getLogger(__name__)

MIN_SCENARIOS = 8
MAX_SCENARIOS = 14


@dataclass
class StoryContext:
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]


class TestCaseGeneratorAgent:
    """
    Generates structured QA test cases from user stories.

    15 scenario categories:
      1  HAPPY_PATH            6  BOUNDARY_EMPTY       11 CLEAR_RESET_ALL
      2  MULTI_COMBINATION     7  MIXED_DATA           12 PERFORMANCE_SCALE
      3  SEQUENTIAL_REFINEMENT 8  ASYNC_TIMING         13 REGRESSION
      4  STATE_PERSISTENCE     9  UI_UX_CONSISTENCY    14 LIFECYCLE_TRANSITION
      5  BUSINESS_RULES        10 REMOVAL_DESELECTION  15 ERROR_FAILURE
    """

    # NOTE: literal braces in the JSON example block are escaped as {{ / }}
    SYSTEM_PROMPT = (
        "You are a senior QA engineer with expertise in writing exhaustive, "
        "production-grade test cases from Agile user stories.\n\n"
        "Your job is to produce a JSON array of test cases that covers ALL of the "
        "following scenario categories (use as many as are relevant to the story):\n\n"
        "SCENARIO TAXONOMY\n"
        "=================\n"
        "1.  HAPPY_PATH              - Core success flow, minimal friction, valid inputs\n"
        "2.  MULTI_COMBINATION       - Multiple related selections / items simultaneously\n"
        "3.  SEQUENTIAL_REFINEMENT   - Chaining / drilling down (e.g. filter A then filter B)\n"
        "4.  STATE_PERSISTENCE       - User selections survive async refreshes / reloads\n"
        "5.  BUSINESS_RULES          - TOP-N limits, ranking logic, count thresholds\n"
        "6.  BOUNDARY_EMPTY          - Single item, zero results, all items, null values\n"
        "7.  MIXED_DATA              - Heterogeneous assets (some have Tag X, some don't)\n"
        "8.  ASYNC_TIMING            - Loader states, partial renders, race conditions\n"
        "9.  UI_UX_CONSISTENCY       - Visual parity, chip/checkbox/toggle styling, spacing\n"
        "10. REMOVAL_DESELECTION     - Undoing a filter, deselecting an option\n"
        "11. CLEAR_RESET_ALL         - Global 'clear filters' returns system to baseline\n"
        "12. PERFORMANCE_SCALE       - Large data sets (hundreds/thousands), response SLA\n"
        "13. REGRESSION              - Existing unrelated features still work as before\n"
        "14. LIFECYCLE_TRANSITION    - Items appear / disappear based on changing context\n"
        "15. ERROR_FAILURE           - Network errors, timeouts, API failures, retries\n\n"
        "RULES\n"
        "=====\n"
        "- Generate between {min_scenarios} and {max_scenarios} test cases per story.\n"
        "- Map every acceptance criterion to at least one test case.\n"
        "- Each test case MUST have a unique snake_case test_case_name.\n"
        "- Steps must be concrete, observable, and UI-action oriented.\n"
        "- expected_result must be a single, verifiable assertion.\n"
        "- Include preconditions where needed (add as step 0 or in remarks).\n"
        "- Never repeat the same scenario twice; vary data, tags, and states.\n\n"
        "OUTPUT FORMAT (return ONLY valid JSON, no markdown, no extra text):\n"
        "[\n"
        "  {{\n"
        "    \"test_scenario\":  \"<category label> - <short description>\",\n"
        "    \"test_case_name\": \"<snake_case_unique_name>\",\n"
        "    \"steps\": [\n"
        "      {{\n"
        "        \"step_no\": 1,\n"
        "        \"description\": \"<action the tester performs>\",\n"
        "        \"expected_result\": \"<observable, verifiable result>\"\n"
        "      }}\n"
        "    ],\n"
        "    \"remarks\": \"<optional: preconditions, test data notes, coverage rationale>\"\n"
        "  }}\n"
        "]\n"
    )

    def __init__(self, openai_api_key: Optional[str] = None):
        api_key = openai_api_key or settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=api_key)
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_test_cases_from_story(self, story) -> List[TestCase]:
        ctx = self._normalise_story(story)
        logger.info(f"Generating test cases for story: [{ctx.id}] {ctx.title}")
        raw = self._call_llm(self._build_generation_prompt(ctx))
        test_cases = self._parse_and_build(raw, ctx)
        logger.info(f"  -> {len(test_cases)} test cases generated")
        return test_cases

    def generate_test_cases_from_stories(self, stories) -> List[TestCase]:
        all_cases: List[TestCase] = []
        for story in stories:
            try:
                all_cases.extend(self.generate_test_cases_from_story(story))
            except Exception as e:
                if isinstance(story, dict):
                    sid = story.get("id", story.get("story_id", "?"))
                else:
                    sid = getattr(story, "id", getattr(story, "story_id", "?"))
                logger.error(f"Failed to generate for story {sid}: {e}", exc_info=True)
        logger.info(f"Total test cases generated: {len(all_cases)}")
        return all_cases

    def modify_test_cases_from_story(
        self,
        existing_test_cases: List[TestCase],
        story,
        modification_hint: str = "",
    ) -> List[TestCase]:
        ctx = self._normalise_story(story)
        logger.info(f"Modifying test cases for story: [{ctx.id}] {ctx.title}")
        existing_json = json.dumps(
            [self._test_case_to_dict(tc) for tc in existing_test_cases], indent=2
        )
        prompt = self._build_modification_prompt(ctx, existing_json, modification_hint)
        raw = self._call_llm(prompt)
        updated = self._parse_and_build(raw, ctx)
        logger.info(f"  -> {len(updated)} test cases after modification")
        return updated

    def validate_test_cases(self, test_cases: List[TestCase]) -> bool:
        for tc in test_cases:
            if not tc.test_scenario or not tc.test_case_name:
                logger.warning(f"Invalid test case: missing scenario or name -> {tc}")
                return False
            if not tc.steps:
                logger.warning(f"Test case '{tc.test_case_name}' has no steps")
                return False
        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _normalise_story(self, story) -> StoryContext:
        if isinstance(story, dict):
            story_id    = story.get("id", story.get("story_id", "unknown"))
            title       = story.get("title", story.get("summary", ""))
            description = story.get("description", "")
            criteria    = story.get("acceptance_criteria", [])
        else:
            story_id    = getattr(story, "id", getattr(story, "story_id", "unknown"))
            title       = getattr(story, "title", getattr(story, "summary", ""))
            description = getattr(story, "description", "")
            criteria    = getattr(story, "acceptance_criteria", [])

        if isinstance(criteria, str):
            criteria = [c.strip() for c in criteria.split(";") if c.strip()]

        if not story_id or str(story_id).strip().lower() in ("unknown", ""):
            story_id = f"CSV-{abs(hash(title)) % 100000}" if title else "CSV-UNKNOWN"

        return StoryContext(
            id=str(story_id),
            title=title,
            description=description,
            acceptance_criteria=criteria,
        )

    def _build_generation_prompt(self, ctx: StoryContext) -> str:
        criteria_block = (
            "\n".join(f"  - {c}" for c in ctx.acceptance_criteria)
            or "  (none provided)"
        )
        return (
            f"Story ID: {ctx.id}\n"
            f"Title: {ctx.title}\n\n"
            f"Description:\n{ctx.description or '(none provided)'}\n\n"
            f"Acceptance Criteria:\n{criteria_block}\n\n"
            f"Generate {MIN_SCENARIOS}-{MAX_SCENARIOS} comprehensive test cases covering all "
            f"relevant scenario categories from the taxonomy. "
            f"Every acceptance criterion must be covered by at least one test case.\n"
        )

    def _build_modification_prompt(
        self, ctx: StoryContext, existing_json: str, hint: str
    ) -> str:
        criteria_block = (
            "\n".join(f"  - {c}" for c in ctx.acceptance_criteria)
            or "  (none provided)"
        )
        hint_block = f"\nChange hint from the team: {hint}" if hint else ""
        return (
            f"Story ID: {ctx.id}\n"
            f"Title: {ctx.title}\n\n"
            f"Updated Description:\n{ctx.description or '(none provided)'}\n\n"
            f"Updated Acceptance Criteria:\n{criteria_block}\n"
            f"{hint_block}\n\n"
            f"EXISTING TEST CASES (JSON):\n{existing_json}\n\n"
            "TASK:\n"
            "1. Keep scenarios that are still fully valid (return them unchanged).\n"
            "2. Update steps/expected results that no longer match the story.\n"
            "3. Add new test cases for acceptance criteria not yet covered.\n"
            "4. Remove any test case that directly contradicts the story.\n"
            "5. Ensure all 15 scenario categories that apply are covered.\n\n"
            "Return the complete updated set as a JSON array in the same format as before.\n"
        )

    def _call_llm(self, user_prompt: str) -> str:
        # str.format() is safe: the only real placeholders are
        # {min_scenarios} and {max_scenarios}; all literal braces
        # in the JSON example have been escaped as {{ and }}.
        system = self.SYSTEM_PROMPT.format(
            min_scenarios=MIN_SCENARIOS,
            max_scenarios=MAX_SCENARIOS,
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        return response.choices[0].message.content.strip()

    def _parse_and_build(self, raw: str, ctx: StoryContext) -> List[TestCase]:
        # Strip markdown fences
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        raw = raw.strip()

        # Attempt 1: direct parse
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Attempt 2: extract first [...] block
            start, end = raw.find("["), raw.rfind("]")
            if start != -1 and end > start:
                try:
                    data = json.loads(raw[start : end + 1])
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error: {e}\nRaw:\n{raw[:500]}")
                    return self._fallback_test_cases(ctx)
            else:
                logger.error(f"No JSON array found in response.\nRaw:\n{raw[:500]}")
                return self._fallback_test_cases(ctx)

        # Normalise wrapper shapes
        if isinstance(data, dict):
            for key in ("test_cases", "cases", "results"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                if all(k in data for k in ("test_scenario", "test_case_name", "steps")):
                    data = [data]
                else:
                    logger.error(f"Unexpected dict shape. Keys: {list(data.keys())}")
                    return self._fallback_test_cases(ctx)

        if not isinstance(data, list):
            logger.error("Response is not a JSON list, using fallback")
            return self._fallback_test_cases(ctx)

        test_cases: List[TestCase] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            steps: List[TestStep] = []
            for idx, s in enumerate(item.get("steps", []), 1):
                if isinstance(s, dict):
                    steps.append(
                        TestStep(
                            step_no=s.get("step_no", idx),
                            description=s.get("description", ""),
                            expected_results=(
                                s.get("expected_result") or s.get("expected_results", "")
                            ),
                        )
                    )
                else:
                    steps.append(
                        TestStep(step_no=idx, description=str(s), expected_results="")
                    )
            if not steps:
                continue
            test_cases.append(
                TestCase(
                    test_scenario=item.get("test_scenario", "Unknown Scenario"),
                    test_case_name=item.get("test_case_name", f"tc_{len(test_cases)+1}"),
                    test_data={"story_id": ctx.id, "story_title": ctx.title},
                    steps=steps,
                    remarks=item.get("remarks", f"Generated from story: {ctx.title}"),
                )
            )

        return test_cases if test_cases else self._fallback_test_cases(ctx)

    def _fallback_test_cases(self, ctx: StoryContext) -> List[TestCase]:
        logger.warning("Using fallback test case due to parse error")
        return [
            TestCase(
                test_scenario="Fallback - Manual Review Required",
                test_case_name=f"fallback_{ctx.id}",
                test_data={"story_id": ctx.id, "story_title": ctx.title},
                steps=[
                    TestStep(
                        step_no=1,
                        description="Manually review the story and create test steps",
                        expected_results="Test case is created with proper steps",
                    )
                ],
                remarks=f"LLM output could not be parsed for story: {ctx.title}",
            )
        ]

    @staticmethod
    def _test_case_to_dict(tc: TestCase) -> dict:
        return {
            "test_scenario":  tc.test_scenario,
            "test_case_name": tc.test_case_name,
            "steps": [
                {
                    "step_no":         s.step_no,
                    "description":     s.description,
                    "expected_result": s.expected_results,
                }
                for s in tc.steps
            ],
            "remarks": tc.remarks or "",
        }