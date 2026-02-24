"""
Test Executor v4 - All bugs fixed.

Fixes:
1. fn_with_data_params: inject actual test_data values as function args
2. _clean_code: properly strips duplicate playwright imports
3. setup_fixture (@pytest.fixture def setup): handles yield-based fixtures
4. Commented-out __main__: strips # if __name__ lines too
5. Screenshot paths: stored as relative 'screenshots/name.png' in TestExecutionResult
   so the HTML report links work in browser
6. _take_screenshot helper injected into every test for reliable failure capture
"""
import logging
import os
import sys
import re
import ast
import textwrap
import time
import traceback
import subprocess
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from models import GeneratedTestCase, TestExecutionResult
from config.settings import settings, TestStatus

logger = logging.getLogger(__name__)


class TestExecutor:

    def __init__(self, reports_folder: str = "./reports"):
        self.reports_folder = os.path.abspath(reports_folder)
        self.screenshots_folder = os.path.join(self.reports_folder, "screenshots")
        os.makedirs(self.reports_folder, exist_ok=True)
        os.makedirs(self.screenshots_folder, exist_ok=True)

    # ------------------------------------------------------------------ Public API

    def execute_batch(self, generated_tests: List[GeneratedTestCase]) -> List[TestExecutionResult]:
        results = []
        total = len(generated_tests)
        for idx, gen_test in enumerate(generated_tests, 1):
            logger.info(f"[{idx}/{total}] Executing: {gen_test.test_case_id}")
            result = self.execute_single(gen_test)
            results.append(result)
            status_word = "PASSED" if result.status == TestStatus.PASSED else "FAILED"
            logger.info(f"  >> {status_word} ({result.duration_seconds:.2f}s)")
            if result.error_message:
                logger.info(f"  Error: {result.error_message[:200]}")
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        logger.info(f"Execution complete: {passed}/{total} passed")
        return results

    def execute_single(self, gen_test: GeneratedTestCase) -> TestExecutionResult:
        start = time.time()
        test_id = gen_test.test_case_id
        logs = []
        # Pre-compute paths - absolute for disk, relative for HTML report
        ss_abs = self._screenshot_abs_path(test_id)
        ss_rel = self._screenshot_rel_path(test_id)

        try:
            code = self._normalize_test_code(gen_test, ss_abs)
            test_file = self._write_test_file(test_id, code)
            logs.append(f"Test file: {test_file}")
            success, output, err_output = self._run_test_file(test_file)
            duration = time.time() - start
            logs.extend([ln for ln in (output + "\n" + err_output).split("\n") if ln.strip()])

            if success:
                return TestExecutionResult(
                    test_case_id=test_id, test_name=test_id,
                    status=TestStatus.PASSED, duration_seconds=duration, logs=logs)
            else:
                # Use relative path in result so HTML report links work
                ss_path_for_report = ss_rel if os.path.exists(ss_abs) else None
                return TestExecutionResult(
                    test_case_id=test_id, test_name=test_id,
                    status=TestStatus.FAILED, duration_seconds=duration,
                    error_message=self._extract_error(err_output or output),
                    screenshot_path=ss_path_for_report,
                    logs=logs)
        except Exception as e:
            duration = time.time() - start
            msg = f"Executor error: {e}"
            logger.error(msg)
            logs.append(traceback.format_exc())
            return TestExecutionResult(
                test_case_id=test_id, test_name=test_id,
                status=TestStatus.FAILED, duration_seconds=duration,
                error_message=msg, logs=logs)

    # ------------------------------------------------------------------ Pattern detection

    def _detect_pattern(self, code: str) -> str:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return "broken"

        has_parametrize = "@pytest.mark.parametrize" in code
        has_playwright = "sync_playwright" in code

        # setup fixture pattern: @pytest.fixture with def setup or yield
        if "@pytest.fixture" in code and re.search(r'def\s+setup\b', code):
            return "setup_fixture"

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                args = [a.arg for a in node.args.args]
                # page fixture: takes exactly 'page', playwright context is external
                if args == ["page"] and not has_parametrize and not has_playwright:
                    return "page_fixture"
                if args == ["page"] and not has_parametrize:
                    return "page_fixture"
                # setup fixture used as arg
                if args == ["setup"] and not has_parametrize:
                    return "setup_fixture"
                # data params: has non-page args + own playwright context
                if args and args != ["page"] and "page" not in args and not has_parametrize and has_playwright:
                    return "fn_with_data_params"

        if has_parametrize:
            return "parametrize"
        if has_playwright:
            return "self_contained"
        return "no_context"

    # ------------------------------------------------------------------ Normalization

    def _normalize_test_code(self, gen_test: GeneratedTestCase, ss_abs: str) -> str:
        code = gen_test.test_code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            code = "\n".join(lines[1:end])

        hl = str(settings.HEADLESS)
        # ELEMENT_TIMEOUT_MS controls per-action Playwright waits (default 10s).
        # TEST_TIMEOUT_SECONDS is only used for the subprocess hard-kill limit.
        # Using TEST_TIMEOUT_SECONDS*1000 here caused every missing element to
        # wait 5 minutes before failing (282 s run for a single test).
        tms = settings.ELEMENT_TIMEOUT_MS
        ssp = ss_abs.replace("\\", "/")  # forward slashes work on Windows too

        pattern = self._detect_pattern(code)
        logger.info(f"  Code pattern: {pattern}")

        if pattern == "page_fixture":
            return self._wrap_page_fixture(code, hl, tms, ssp)
        elif pattern == "fn_with_data_params":
            return self._wrap_fn_with_data_params(code, gen_test.test_data or {}, hl, tms, ssp)
        elif pattern == "parametrize":
            return self._wrap_parametrize(code, gen_test.test_data or {}, hl, tms, ssp)
        elif pattern == "setup_fixture":
            return self._wrap_setup_fixture(code, hl, tms, ssp)
        elif pattern == "self_contained":
            return self._wrap_self_contained(code, ssp)
        else:
            return self._wrap_no_context(code, hl, tms, ssp)

    # ------------------------------------------------------------------ Code cleaning

    def _clean_code(self, code: str) -> str:
        """
        Remove ALL pytest artifacts, duplicate imports, and existing __main__ block.
        Returns clean function definitions ready to have a fresh __main__ added.
        """
        # 1. Strip non-parametrize @pytest.mark decorators (line-by-line to be safe)
        lines = code.split("\n")
        cleaned_lines = []
        for line in lines:
            if re.match(r'\s*@pytest\.mark\.(?!parametrize)', line):
                continue
            cleaned_lines.append(line)
        code = "\n".join(cleaned_lines)

        # 2. Strip @pytest.fixture blocks (decorator + function + body)
        #    Use bracket/indent counting to find the full block
        code = self._strip_fixture_blocks(code)

        # 3. Remove ALL playwright imports (we'll add exactly one)
        code = re.sub(r'^from playwright\.sync_api[^\n]*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'^import playwright[^\n]*\n?', '', code, flags=re.MULTILINE)

        # 4. Remove pytest imports
        code = re.sub(r'^import pytest\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'^from pytest[^\n]*\n?', '', code, flags=re.MULTILINE)

        # 5. Remove existing __main__ block (including commented-out ones)
        # Find the last top-level if __name__ block (commented or not)
        code = re.sub(r'\n#\s*if __name__.*', '', code, flags=re.DOTALL)
        code = re.sub(r'\n#\s*    .*', '', code)
        main_match = re.search(r'\nif __name__\s*==\s*["\']__main__["\']', code)
        if main_match:
            code = code[:main_match.start()]

        return code.strip()

    def _strip_fixture_blocks(self, code: str) -> str:
        """Remove @pytest.fixture decorated function blocks using indentation tracking."""
        result = []
        lines = code.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if re.match(r'\s*@pytest\.fixture', line):
                # Skip decorator + function body
                i += 1
                # Skip the def line
                while i < len(lines) and not lines[i].strip().startswith("def "):
                    i += 1
                if i < len(lines):
                    i += 1  # skip the def line itself
                    # Skip body (indented lines)
                    while i < len(lines) and (not lines[i].strip() or lines[i][0] in (' ', '\t')):
                        i += 1
            else:
                result.append(line)
                i += 1
        return "\n".join(result)

    def _header(self) -> str:
        # Inject the project root into sys.path so 'config' (and other local
        # packages) are always importable, regardless of the subprocess cwd.
        project_root = os.path.dirname(self.reports_folder)
        return (
            "import sys, traceback, os\n"
            f"sys.path.insert(0, {repr(project_root)})  # ensure project root is importable\n"
            "from playwright.sync_api import sync_playwright, expect\n"
            "import re\n"
        )

    def _screenshot_helper(self, ssp: str) -> str:
        """Global _page var + helper so any exception path can capture a screenshot."""
        return (
            "\n_page = None\n\n"
            "def _take_screenshot(path):\n"
            "    global _page\n"
            "    if _page:\n"
            "        try:\n"
            "            os.makedirs(os.path.dirname(path), exist_ok=True)\n"
            "            _page.screenshot(path=path, full_page=True)\n"
            f'            print(f"SCREENSHOT: {{path}}")\n'
            "        except Exception:\n"
            "            pass\n"
            "\n"
            "def _dump_debug():\n"
            "    global _page\n"
            "    if not _page:\n"
            "        return\n"
            "    try:\n"
            "        _page.wait_for_load_state('domcontentloaded', timeout=2000)\n"
            "    except Exception:\n"
            "        pass\n"
            "    try:\n"
            "        print(f\"DEBUG_URL: {_page.url}\")\n"
            "    except Exception:\n"
            "        pass\n"
        )

    def _make_browser_block(self, hl: str, tms: int) -> str:
        # NOTE: 'hl' is passed in from settings.HEADLESS (as a string).
        # To see the browser during execution, set HEADLESS=false in your .env file.
        return (
            f"    with sync_playwright() as _pw:\n"
            f"        _browser = _pw.{settings.BROWSER_TYPE}.launch(headless={hl})\n"
            f"        _ctx = _browser.new_context(\n"
            f'            viewport={{"width": 1280, "height": 720}},\n'
            f"            ignore_https_errors=True,\n"
            f"        )\n"
            f"        _ctx.set_default_timeout({tms})\n"
            f"        page = _ctx.new_page()\n"
            f"        _page = page\n"
            f"        page.on('framenavigated', lambda frame: print(f\"NAVIGATED: {{frame.url}}\", flush=True) if frame == page.main_frame else None)\n"
            f"        page.on('console', lambda msg: print(f\"CONSOLE: {{msg.type}} {{msg.text}}\", flush=True))\n"
            f"        page.on('pageerror', lambda err: print(f\"PAGEERROR: {{err}}\", flush=True))\n"
            f"        print(f\"START_URL: {{page.url}}\", flush=True)\n"
        )

    def _make_main_wrapper(self, inner_call: str, ssp: str) -> str:
        """Wrap inner_call in __main__ with proper try/finally and screenshot on fail."""
        # Ensure inner_call is indented under the try block
        inner_call = inner_call.rstrip()
        inner_call = textwrap.indent(inner_call, "    ") if inner_call else ""
        return (
            '\nif __name__ == "__main__":\n'
            "    _exit = 0\n"
            "    try:\n"
            f"{inner_call}\n"
            '        print("TEST_STATUS: PASSED")\n'
            "    except Exception as _e:\n"
            '        print("TEST_STATUS: FAILED")\n'
            '        print(f"ERROR: {_e}")\n'
            "        traceback.print_exc()\n"
            "        _dump_debug()\n"
            f'        _take_screenshot(r"{ssp}")\n'
            "        _exit = 1\n"
            "    sys.exit(_exit)\n"
        )

    def _make_main_wrapper_no_screenshot(self, inner_call: str, ssp: str) -> str:
        """
        Like _make_main_wrapper but WITHOUT calling _take_screenshot in the except.
        Use this when screenshot is already captured inside the inner try/except
        (before browser.close()) to avoid TargetClosedError.
        """
        inner_call = inner_call.rstrip()
        inner_call = textwrap.indent(inner_call, "    ") if inner_call else ""
        return (
            '\nif __name__ == "__main__":\n'
            "    _exit = 0\n"
            "    try:\n"
            f"{inner_call}\n"
            '        print("TEST_STATUS: PASSED")\n'
            "    except Exception as _e:\n"
            '        print("TEST_STATUS: FAILED")\n'
            '        print(f"ERROR: {_e}")\n'
            "        traceback.print_exc()\n"
            "        _exit = 1\n"
            "    sys.exit(_exit)\n"
        )



    def _wrap_page_fixture(self, code, hl, tms, ssp):
        """def test_foo(page): ... with external playwright context needed."""
        m = re.search(r"def (test_\w+)\s*\(\s*page\s*\)", code)
        fn = m.group(1) if m else "test_main"
        cleaned = self._clean_code(code)

        browser_block = self._make_browser_block(hl, tms)
        # FIX: screenshot is taken BEFORE browser closes (inside except), not after.
        # Old pattern closed the browser in finally then tried to screenshot in
        # the outer except — causing TargetClosedError on every failing test.
        inner = (
            browser_block +
            "        try:\n"
            f"            {fn}(page)\n"
            "        except Exception:\n"
            f"            _take_screenshot(r\"{ssp}\")\n"
            "            raise\n"
            "        finally:\n"
            "            try: _ctx.close()\n"
            "            except Exception: pass\n"
            "            try: _browser.close()\n"
            "            except Exception: pass\n"
        )
        return self._header() + self._screenshot_helper(ssp) + "\n" + cleaned + "\n" + self._make_main_wrapper_no_screenshot(inner, ssp)

    def _wrap_fn_with_data_params(self, code, test_data: dict, hl, tms, ssp):
        """
        def test_foo(param1, param2, ...): with sync_playwright() inside.
        Injects actual values: test_data first, then settings defaults.
        """
        m = re.search(r"def (test_\w+)\s*\(([^)]+)\)", code)
        if not m:
            return self._wrap_self_contained(code, ssp)

        fn = m.group(1)
        param_names = [p.strip() for p in m.group(2).split(",") if p.strip()]

        # Build value lookup: test_data takes priority, then settings defaults
        value_map = {
            "base_url": settings.BASE_URL,
            "url": settings.BASE_URL,
            "login_url": settings.BASE_URL,
            "login_email": settings.LOGIN_EMAIL,
            "email": settings.LOGIN_EMAIL,
            "username": settings.LOGIN_EMAIL,
            "login_password": settings.LOGIN_PASSWORD,
            "password": settings.LOGIN_PASSWORD,
            "old_password": settings.LOGIN_PASSWORD,
            "existing_password": settings.LOGIN_PASSWORD,
            "current_password": settings.LOGIN_PASSWORD,
            "new_password": "NewTestPass@2024",
            "confirm_password": "NewTestPass@2024",
            "new_weak_password": "weak",
            "confirm_new_weak_password": "weak",
            "incorrect_password": "WrongPassword123",
            "incorrect_existing_password": "WrongPassword123",
            "search_query": "test",
            "search_criteria": "test asset",
            "vectorisation_query": "find duplicates",
            "error_message": "Error",
            "error_message_text": "Please select assets",
        }
        # test_data overrides defaults (cast all to str)
        if test_data:
            value_map.update({k: str(v) for k, v in test_data.items() if v is not None})

        assignments = []
        call_args = []
        for pname in param_names:
            val = value_map.get(pname, f"TEST_{pname.upper()}")
            assignments.append(f"        {pname} = {repr(str(val))}")
            call_args.append(pname)

        cleaned = self._clean_code(code)
        assign_block = "\n".join(assignments)
        call_line = f"        {fn}({', '.join(call_args)})"
        inner = assign_block + "\n" + call_line

        return self._header() + self._screenshot_helper(ssp) + "\n" + cleaned + "\n" + self._make_main_wrapper(inner, ssp)

    def _wrap_parametrize(self, code, test_data: dict, hl, tms, ssp):
        """@pytest.mark.parametrize(...) def test_foo(...)"""
        names, vals = self._extract_parametrize_values(code)
        m = re.search(r"def (test_\w+)\s*\(([^)]*)\)", code)
        fn = m.group(1) if m else "test_main"
        fn_args = [a.strip() for a in (m.group(2) if m else "").split(",") if a.strip()]
        fn_takes_page = bool(fn_args) and fn_args[0] == "page"
        fn_has_pw = "sync_playwright" in code

        cleaned = self._strip_parametrize_decorator(code)
        cleaned = self._clean_code(cleaned)

        if names and vals:
            assignments = "\n".join(f"        {n} = {repr(v)}" for n, v in zip(names, vals))
            call_args = ", ".join(names)
        else:
            assignments = ""
            call_args = ""

        if fn_has_pw and not fn_takes_page:
            call_line = f"        {fn}({call_args})" if call_args else f"        {fn}()"
            inner = (assignments + "\n" + call_line) if assignments else call_line
        else:
            browser_block = self._make_browser_block(hl, tms)
            page_call = f"page, {call_args}" if call_args else "page"
            inner = (
                f"        {assignments.strip()}\n" if assignments else ""
            ) + (
            browser_block +
            "        try:\n"
            f"            {fn}({page_call})\n"
            "        finally:\n"
            "            _ctx.close(); _browser.close()\n"
        )

        return self._header() + self._screenshot_helper(ssp) + "\n" + cleaned + "\n" + self._make_main_wrapper(inner, ssp)

    def _wrap_setup_fixture(self, code, hl, tms, ssp):
        """
        @pytest.fixture def setup(): yield page  +  def test_foo(setup):
        Strips the fixture entirely, injects a real playwright page as 'setup' arg.
        """
        # Find test function that takes setup
        m = re.search(r"def (test_\w+)\s*\(\s*setup\s*\)", code)
        fn = m.group(1) if m else "test_main"
        cleaned = self._clean_code(code)

        browser_block = self._make_browser_block(hl, tms)
        inner = (
            browser_block +
            "        try:\n"
            f"            {fn}(page)  # 'setup' fixture yields page - we pass page directly\n"
            "        except Exception:\n"
            f"            _take_screenshot(r\"{ssp}\")\n"
            "            raise\n"
            "        finally:\n"
            "            try: _ctx.close()\n"
            "            except Exception: pass\n"
            "            try: _browser.close()\n"
            "            except Exception: pass\n"
        )
        return self._header() + self._screenshot_helper(ssp) + "\n" + cleaned + "\n" + self._make_main_wrapper_no_screenshot(inner, ssp)

    def _wrap_self_contained(self, code, ssp):
        """def test_foo(): with sync_playwright() inside - just add __main__."""
        cleaned = self._clean_code(code)
        m = re.search(r"def (test_\w+)\s*\(\s*\)", cleaned)
        fn = m.group(1) if m else None

        if fn:
            inner = f"        {fn}()"
        else:
            inner = "        pass  # no test function found"

        return self._header() + self._screenshot_helper(ssp) + "\n" + cleaned + "\n" + self._make_main_wrapper(inner, ssp)

    def _wrap_no_context(self, code, hl, tms, ssp):
        """No playwright at all - full wrapper."""
        m = re.search(r"def (test_\w+)", code)
        fn = m.group(1) if m else "test_main"
        cleaned = self._clean_code(code)

        browser_block = self._make_browser_block(hl, tms)
        inner = (
            browser_block +
            "        try:\n"
            f"            {fn}(page)\n"
            "        except TypeError:\n"
            f"            {fn}()\n"
            "        except Exception:\n"
            f"            _take_screenshot(r\"{ssp}\")\n"
            "            raise\n"
            "        finally:\n"
            "            try: _ctx.close()\n"
            "            except Exception: pass\n"
            "            try: _browser.close()\n"
            "            except Exception: pass\n"
        )
        return self._header() + self._screenshot_helper(ssp) + "\n" + cleaned + "\n" + self._make_main_wrapper_no_screenshot(inner, ssp)

    # ------------------------------------------------------------------ Parametrize helpers

    def _strip_parametrize_decorator(self, code: str) -> str:
        """Remove @pytest.mark.parametrize(...) using bracket counting."""
        lines = code.split("\n")
        result, skip, depth = [], False, 0
        for line in lines:
            if not skip and line.strip().startswith("@pytest.mark.parametrize"):
                skip = True
                depth = line.count("(") - line.count(")")
                if depth <= 0:
                    skip = False
                continue
            if skip:
                depth += line.count("(") - line.count(")")
                if depth <= 0:
                    skip = False
                continue
            result.append(line)
        return "\n".join(result)

    def _extract_parametrize_values(self, code: str):
        """Extract first row of values from @pytest.mark.parametrize."""
        start = code.find("@pytest.mark.parametrize")
        if start == -1:
            return [], []
        depth, i = 0, start
        while i < len(code):
            depth += (1 if code[i] == "(" else -1 if code[i] == ")" else 0)
            if depth == 0 and i > start:
                break
            i += 1
        flat = " ".join(code[start:i+1].split())
        names_m = re.search(r'parametrize\(\s*["\']([^"\']+)["\']', flat)
        if not names_m:
            return [], []
        names = [n.strip() for n in names_m.group(1).split(",")]
        vals_m = re.search(r'\[\s*\(([^)]+)\)', flat)
        if not vals_m:
            return names, []
        raw = vals_m.group(1)
        vals = re.findall(r'"([^"]*)"', raw) or re.findall(r"'([^']*)'", raw)
        if not vals:
            vals = [v.strip().strip("\"'") for v in raw.split(",")]
        return names, vals

    # ------------------------------------------------------------------ File I/O

    def _write_test_file(self, test_id, code):
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', test_id)[:50]
        path = os.path.abspath(os.path.join(self.reports_folder, f"_run_{safe}.py"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return path

    def _run_test_file(self, test_file):
        timeout = settings.TEST_TIMEOUT_SECONDS + 30
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # FIX: Use project root as cwd so 'config' package is importable.
        # reports/ is a sub-folder of the project root; running from there
        # causes "ModuleNotFoundError: No module named 'config'" because
        # Python looks for packages relative to cwd.
        project_root = os.path.dirname(self.reports_folder)
        try:
            r = subprocess.run(
                [sys.executable, test_file],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout, env=env,
                cwd=project_root,
            )
            out, err = r.stdout or "", r.stderr or ""
            success = r.returncode == 0 and "TEST_STATUS: FAILED" not in (out + err)
            return success, out, err
        except subprocess.TimeoutExpired as e:
            out = e.stdout or ""
            err = e.stderr or ""
            return False, out, (err + ("\n" if err else "") + f"Timed out after {timeout}s")
        except Exception as e:
            return False, "", f"Subprocess error: {e}"

    def _screenshot_abs_path(self, test_id: str) -> str:
        """Absolute path used for actually saving the screenshot file."""
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', test_id)[:40]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.abspath(
            os.path.join(self.screenshots_folder, f"{safe}_{ts}.png")
        )

    def _screenshot_rel_path(self, test_id: str) -> str:
        """
        Relative path stored in TestExecutionResult.screenshot_path.
        The HTML report is at reports/report.html
        The screenshot is at reports/screenshots/name.png
        So relative path from report = screenshots/name.png
        """
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', test_id)[:40]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"screenshots/{safe}_{ts}.png"

    def _extract_error(self, output):
        if not output:
            return "Unknown error"
        lines = [ln.strip() for ln in output.strip().split("\n") if ln.strip()]
        for ln in lines:
            if ln.startswith("ERROR:"):
                return ln[6:].strip()
        for i, ln in enumerate(lines):
            if any(kw in ln for kw in ["Error:", "Exception:", "AssertionError", "TimeoutError"]):
                return " | ".join(lines[i:i+3])[:500]
        return " | ".join(lines[-3:])[:500]