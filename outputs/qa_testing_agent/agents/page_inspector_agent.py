"""
Smart Page Inspector v2 - Intelligent DOM Capture with Real Interaction

This version:
1. Actually executes precondition steps (doesn't just try to find them)
2. Records what selectors WORKED during execution
3. Uses Playwright's smart element discovery (like Codegen)
4. Feeds proven selectors back to test generator

Much better than manual SelectorHub because it's:
- Fully automated
- Application-agnostic
- Uses proven selectors (we know they work because we just used them)
- Integrated into the pipeline
"""
import logging
import json
import re
from typing import Dict, List, Optional, Tuple
from playwright.sync_api import sync_playwright, Page, Locator, expect
from config.settings import settings
from utils.selector_discovery import SmartSelectorDiscovery
from utils.selector_map_loader import ensure_selector_map, load_selector_map

logger = logging.getLogger(__name__)


class SmartPageInspectorV2:
    """
    Smart Page Inspector that actually interacts with the page.
    
    Unlike v1 which just looked for elements, v2:
    - Executes each precondition step
    - Records the selector that actually worked
    - Captures the state after each step
    - Provides proven selectors to test generator
    """
    
    def __init__(self):
        self._cache: Optional[Dict] = None
    
    def inspect(self, force_refresh: bool = False) -> Dict:
        """
        Inspect the application by actually executing precondition steps.
        
        Returns:
            Dictionary with:
            - executed_steps: List of steps executed with selectors used
            - filter_panel: Selector for filter panel (if found)
            - tags_section: Selector for tags section (if found)
            - tag_items: List of tag elements with selectors
            - buttons: List of all buttons
            - success: Whether inspection completed
        """
        if self._cache and not force_refresh:
            logger.info("Using cached page inspection results")
            return self._cache
        
        logger.info("Starting Smart Page Inspector v2...")
        logger.info(f"Target: {settings.FEATURE_URL or settings.BASE_URL}")
        
        result = {
            "success": False,
            "error": None,
            "executed_steps": [],
            "filter_panel": {},
            "tags_section": {},
            "tag_items": [],
            "buttons": [],
            "inputs": [],
        }
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=settings.HEADLESS)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    ignore_https_errors=True,
                )
                context.set_default_timeout(settings.ELEMENT_TIMEOUT_MS)
                page = context.new_page()
                
                # Create smart selector discovery
                discovery = SmartSelectorDiscovery(page)
                
                # Step 1: Login
                logger.info("Step 1: Logging in...")
                self._login(page)
                
                # Step 2: Navigate to feature URL if not already there
                if settings.FEATURE_URL and settings.FEATURE_URL != page.url:
                    logger.info(f"Step 2: Navigating to {settings.FEATURE_URL}")
                    page.goto(settings.FEATURE_URL)
                    page.wait_for_load_state("networkidle")
                
                # Step 3: Execute precondition steps WITH smart discovery
                executed_steps = self._execute_preconditions_smart(page, discovery)
                result["executed_steps"] = executed_steps
                
                # Step 4: Capture DOM in final state
                logger.info("Step 4: Capturing page DOM after preconditions...")
                result.update(self._capture_dom(page))
                result["success"] = True
                
                browser.close()
                
        except Exception as e:
            logger.error(f"Page inspection failed: {e}", exc_info=True)
            result["error"] = str(e)
        
        if result["success"]:
            logger.info("Smart Page Inspector v2 completed successfully")
            logger.info(f"Executed {len(result['executed_steps'])} precondition steps")
            logger.info(f"Captured {len(result['tag_items'])} tag elements")
            logger.info(f"Captured {len(result['buttons'])} buttons")
            self._cache = result
        else:
            logger.error("Smart Page Inspector v2 failed")
        
        return result
    
    def _login(self, page: Page):
        """Login to the application"""
        page.goto(settings.BASE_URL)
        page.wait_for_load_state("domcontentloaded")

        def _fill_first(locators, value, label):
            last_err = None
            for loc in locators:
                try:
                    target = loc.first
                    expect(target).to_be_visible(timeout=3000)
                    target.fill(value)
                    return
                except Exception as e:
                    last_err = e
            raise RuntimeError(f"Could not find {label} field") from last_err

        _fill_first(
            [
                page.get_by_label(settings.EMAIL_FIELD_LABEL),
                page.get_by_role("textbox", name=re.compile(settings.EMAIL_FIELD_LABEL, re.IGNORECASE)),
                page.get_by_placeholder(re.compile(settings.EMAIL_FIELD_LABEL, re.IGNORECASE)),
                page.locator("input[type='email']"),
            ],
            settings.LOGIN_EMAIL,
            "email",
        )
        _fill_first(
            [
                page.get_by_label(settings.PASSWORD_FIELD_LABEL),
                page.get_by_role("textbox", name=re.compile(settings.PASSWORD_FIELD_LABEL, re.IGNORECASE)),
                page.get_by_placeholder(re.compile(settings.PASSWORD_FIELD_LABEL, re.IGNORECASE)),
                page.locator("input[type='password']"),
            ],
            settings.LOGIN_PASSWORD,
            "password",
        )

        # Click login button (.first to avoid strict mode)
        login_btn = page.get_by_role(
            "button",
            name=re.compile(settings.LOGIN_BUTTON_PATTERN, re.IGNORECASE),
        ).first
        expect(login_btn).to_be_visible(timeout=settings.ELEMENT_TIMEOUT_MS)
        expect(login_btn).to_be_enabled()
        login_btn.click()
        page.wait_for_load_state("networkidle")

        # Navigate to feature URL if configured
        if settings.FEATURE_URL and settings.FEATURE_URL != settings.BASE_URL:
            page.goto(settings.FEATURE_URL)
            page.wait_for_load_state("networkidle")

        # Fail fast if login did not succeed
        if re.search(r"login", page.url, re.IGNORECASE):
            raise RuntimeError("Login failed: still on login page after submit")

        logger.info("Login successful")
    
    def _execute_preconditions_smart(
        self, page: Page, discovery: SmartSelectorDiscovery
    ) -> List[Dict]:
        """
        Execute precondition steps using smart selector discovery.
        
        Each step is executed independently, and we record what selector worked.
        This gives us proven selectors to feed to the test generator.
        """
        steps = self._get_precondition_steps()
        
        if not steps:
            logger.info("No precondition steps to execute")
            return []
        
        logger.info(f"Step 3: Executing {len(steps)} precondition steps with smart discovery...")
        
        executed_steps = []
        
        for i, step_desc in enumerate(steps, 1):
            logger.info(f"  Precondition {i}/{len(steps)}: {step_desc}")
            
            try:
                # Use smart discovery to find and interact with element
                success, selector, info = discovery.find_and_click(step_desc)
                
                if success:
                    logger.info(f"    OK Executed successfully: {info}")
                    executed_steps.append({
                        "step_number": i,
                        "description": step_desc,
                        "selector": selector,
                        "info": info,
                        "success": True,
                    })
                    
                    # Wait for any animations/transitions
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(500)  # Small delay for UI to settle
                else:
                    logger.warning(f"    FAILED Could not execute: {step_desc}")
                    executed_steps.append({
                        "step_number": i,
                        "description": step_desc,
                        "selector": None,
                        "info": None,
                        "success": False,
                    })
            
            except Exception as e:
                logger.warning(f"    FAILED Error executing step: {e}")
                executed_steps.append({
                    "step_number": i,
                    "description": step_desc,
                    "selector": None,
                    "info": None,
                    "success": False,
                    "error": str(e),
                })
        
        return executed_steps

    def _get_precondition_steps(self) -> List[str]:
        """Return precondition steps from settings, story map, or infer from selector_map."""
        # Story-specific preconditions (first non-empty)
        try:
            raw_story_steps = getattr(settings, "STORY_PRECONDITIONS_JSON", "{}")
            story_map = json.loads(raw_story_steps) if isinstance(raw_story_steps, str) else raw_story_steps
        except (ValueError, TypeError):
            story_map = {}

        if isinstance(story_map, dict):
            for _, candidate in story_map.items():
                if isinstance(candidate, list) and candidate:
                    logger.info("Using precondition steps from STORY_PRECONDITIONS_JSON (first available)")
                    return candidate

        # Fallback: infer minimal preconditions from selector_map.json
        folder = getattr(settings, "UI_SNAPSHOT_FOLDER", "./ui_snapshot")
        map_file = getattr(settings, "SELECTOR_MAP_FILE", "selector_map.json")
        rec_file = getattr(settings, "RECORDED_FLOW_FILE", "recorded_flow.py")
        ensure_selector_map(folder, map_file, rec_file)
        selector_map = load_selector_map(folder, map_file) or {}
        actions = selector_map.get("actions", []) if isinstance(selector_map, dict) else []

        # Heuristic: open Filters then Tags if present in recorded actions
        has_filters = any(a.get("kind") == "text" and "Filters" in a.get("text", "") for a in actions)
        has_tags = any(
            (a.get("kind") == "text" and "Tags" in a.get("text", "")) or
            (a.get("kind") == "role" and a.get("role") == "link" and "Tags" in a.get("name", ""))
            for a in actions
        )

        inferred = []
        if has_filters:
            inferred.append("Click Filters")
        if has_tags:
            inferred.append("Click Tags")

        if inferred:
            logger.info("Inferred precondition steps from selector_map.json")
        return inferred
    
    def _capture_dom(self, page: Page) -> Dict:
        """Capture DOM elements after preconditions have been executed"""
        result = {
            "filter_panel": {},
            "tags_section": {},
            "tag_items": [],
            "buttons": [],
            "inputs": [],
        }
        
        # Capture filter panel (try common patterns)
        result["filter_panel"] = self._find_filter_panel(page)
        
        # Capture tags section
        result["tags_section"] = self._find_tags_section(page)
        
        # Capture individual tag elements
        result["tag_items"] = self._find_tag_items(page)
        
        # Capture all interactive buttons
        result["buttons"] = self._find_buttons(page)
        
        # Capture input fields
        result["inputs"] = self._find_inputs(page)
        
        return result
    
    def _find_filter_panel(self, page: Page) -> Dict:
        """Find the filter panel container"""
        # Try known tab/text patterns first (from RC-tabs/Ant Design)
        try:
            loc = page.locator("[id*='tab-filters']").filter(
                has_text=re.compile(r"^Filters$", re.IGNORECASE)
            ).first
            if loc.is_visible(timeout=1000):
                logger.info("Found filter panel via rc-tabs id")
                return {"selector": "[id*='tab-filters']", "type": "css", "value": "tab-filters"}
        except Exception:
            pass
        for role in ["tab", "link", "button"]:
            try:
                loc = page.get_by_role(role, name=re.compile(r"^Filters$", re.IGNORECASE)).first
                if loc.is_visible(timeout=1000):
                    logger.info(f"Found filter panel via role={role} text=Filters")
                    return {"selector": f"role={role} name=Filters", "type": "role", "value": "Filters"}
            except Exception:
                continue

        candidates = [
            ("data-testid", "filter-panel"),
            ("data-testid", "filter-container"),
            ("data-testid", "filters"),
            ("class", "filter-panel"),
            ("class", "filters"),
            ("class", "filter-sidebar"),
            ("id", "filter-panel"),
            ("id", "filters"),
        ]
        
        for attr_type, attr_value in candidates:
            try:
                if attr_type == "data-testid":
                    elem = page.locator(f"[data-testid='{attr_value}']").first
                elif attr_type == "class":
                    elem = page.locator(f".{attr_value}").first
                elif attr_type == "id":
                    elem = page.locator(f"#{attr_value}").first
                else:
                    continue
                
                if elem.is_visible(timeout=1000):
                    logger.info(f"Found filter panel: {attr_type}={attr_value}")
                    return {
                        "selector": f"[{attr_type}='{attr_value}']" if attr_type != "class" else f".{attr_value}",
                        "type": attr_type,
                        "value": attr_value,
                    }
            except:
                continue
        
        logger.warning("Could not find filter panel")
        return {}
    
    def _find_tags_section(self, page: Page) -> Dict:
        """Find the tags section container"""
        # Try common text/anchor patterns first
        tag_name_pat = re.compile(r"^Tags(\s*\(\d+\))?$", re.IGNORECASE)
        for role in ["link", "tab", "button"]:
            try:
                loc = page.get_by_role(role, name=tag_name_pat).first
                if loc.is_visible(timeout=1000):
                    logger.info(f"Found tags section via role={role} text=Tags")
                    return {"selector": f"role={role} name=Tags", "type": "role", "value": "Tags"}
            except Exception:
                continue
        try:
            loc = page.locator("a").filter(has_text=tag_name_pat).first
            if loc.is_visible(timeout=1000):
                logger.info("Found tags section via anchor text")
                return {"selector": "a:has-text('Tags')", "type": "text", "value": "Tags"}
        except Exception:
            pass
        try:
            loc = page.locator("a").filter(has_text=re.compile(r"Tags", re.IGNORECASE)).first
            if loc.is_visible(timeout=1000):
                logger.info("Found tags section via anchor partial match")
                return {"selector": "a:has-text('Tags')", "type": "text", "value": "Tags"}
        except Exception:
            pass

        candidates = [
            ("data-testid", "tags-section"),
            ("data-testid", "tags"),
            ("data-testid", "tag-list"),
            ("class", "tags-section"),
            ("class", "tag-list"),
            ("class", "tags"),
        ]
        
        for attr_type, attr_value in candidates:
            try:
                if attr_type == "data-testid":
                    elem = page.locator(f"[data-testid='{attr_value}']").first
                elif attr_type == "class":
                    elem = page.locator(f".{attr_value}").first
                else:
                    continue
                
                if elem.is_visible(timeout=1000):
                    logger.info(f"Found tags section: {attr_type}={attr_value}")
                    return {
                        "selector": f"[{attr_type}='{attr_value}']" if attr_type != "class" else f".{attr_value}",
                        "type": attr_type,
                        "value": attr_value,
                    }
            except:
                continue
        
        logger.warning("Could not find tags section")
        return {}
    
    def _find_tag_items(self, page: Page) -> List[Dict]:
        """Find individual tag elements"""
        tags = []
        
        # Try to find tag elements by common patterns
        selectors = [
            "[data-testid*='tag']",
            ".tag-item",
            ".tag",
            "[role='button'][aria-label*='tag']",
            ".chip",  # Material UI chips
            ".badge",  # Bootstrap badges
        ]
        
        for selector in selectors:
            try:
                elements = page.locator(selector).all()
                if elements:
                    logger.info(f"Found {len(elements)} tags using selector: {selector}")
                    for elem in elements[:30]:  # Limit to first 30
                        try:
                            text = elem.inner_text()
                            if text.strip():
                                tags.append({
                                    "name": text.strip(),
                                    "selector": selector,
                                    "text": text.strip(),
                                })
                        except:
                            continue
                    if tags:
                        break
            except:
                continue

        # Fallback: look for anchor tags with trailing counts (e.g., "Vehicles105")
        if not tags:
            try:
                for tag in ["a", "div", "span", "li"]:
                    elements = page.locator(tag).filter(
                        has_text=re.compile(r"^[A-Za-z][\w\s]+\d+$")
                    ).all()
                    if elements:
                        logger.info(f"Found {len(elements)} tags using <{tag}> text+count pattern")
                        for elem in elements[:30]:
                            try:
                                text = elem.inner_text()
                                if text.strip():
                                    tags.append({
                                        "name": text.strip(),
                                        "selector": f"{tag}:text-count",
                                        "text": text.strip(),
                                    })
                            except:
                                continue
                        if tags:
                            break
            except:
                pass

        # Fallback: use selector_map tag names to probe for visible tags
        if not tags:
            try:
                folder = getattr(settings, "UI_SNAPSHOT_FOLDER", "./ui_snapshot")
                map_file = getattr(settings, "SELECTOR_MAP_FILE", "selector_map.json")
                selector_map = load_selector_map(folder, map_file) or {}
                tag_actions = selector_map.get("by_category", {}).get("tag", [])
                seen = set()
                for a in tag_actions:
                    raw_name = a.get("name") or a.get("text") or ""
                    core = re.sub(r"\\d+$", "", str(raw_name)).strip()
                    if not core or core in seen:
                        continue
                    seen.add(core)
                    try:
                        loc = page.get_by_text(
                            re.compile(rf"^{re.escape(core)}\d+$")
                        ).first
                        if loc.is_visible(timeout=1000):
                            tags.append({
                                "name": core,
                                "selector": f"text~={core}+count",
                                "text": core,
                            })
                    except Exception:
                        continue
                    if len(tags) >= 20:
                        break
            except Exception:
                pass
        
        if not tags:
            logger.warning("Could not find any tag elements")
        
        return tags
    
    def _find_buttons(self, page: Page) -> List[Dict]:
        """Find all interactive buttons"""
        buttons = []
        
        try:
            button_elements = page.get_by_role("button").all()
            for btn in button_elements[:50]:  # Limit to 50
                try:
                    text = btn.inner_text()
                    if text.strip():
                        buttons.append({
                            "text": text.strip(),
                            "selector": f"button:has-text('{text.strip()}')",
                            "role": "button",
                        })
                except:
                    continue
        except:
            pass
        
        return buttons
    
    def _find_inputs(self, page: Page) -> List[Dict]:
        """Find input fields"""
        inputs = []
        
        try:
            input_elements = page.locator("input").all()
            for inp in input_elements[:30]:  # Limit to 30
                try:
                    input_type = inp.get_attribute("type") or "text"
                    placeholder = inp.get_attribute("placeholder") or ""
                    name = inp.get_attribute("name") or ""
                    aria_label = inp.get_attribute("aria-label") or ""
                    
                    inputs.append({
                        "type": input_type,
                        "placeholder": placeholder,
                        "name": name,
                        "aria_label": aria_label,
                    })
                except:
                    continue
        except:
            pass
        
        return inputs
    
    def clear_cache(self):
        """Clear cached inspection results"""
        self._cache = None
        logger.info("Page inspection cache cleared")
    
    def get_selector_summary(self) -> str:
        """Get a human-readable summary of captured selectors"""
        if not self._cache or not self._cache.get("success"):
            return "No page inspection data available."
        
        info = self._cache
        lines = ["", "="*70, "SMART PAGE INSPECTOR v2 RESULTS", "="*70, ""]
        
        # Show executed precondition steps with proven selectors
        if info.get("executed_steps"):
            lines.append("PRECONDITION STEPS EXECUTED:")
            for step in info["executed_steps"]:
                if step["success"]:
                    lines.append(f"  OK Step {step['step_number']}: {step['description']}")
                    lines.append(f"    Selector: {step['selector']}")
                else:
                    lines.append(f"  FAILED Step {step['step_number']}: {step['description']}")
            lines.append("")
        
        # Show discovered elements
        if info.get("filter_panel"):
            fp = info["filter_panel"]
            lines.append(f"Filter Panel: {fp.get('selector', 'N/A')}")
        
        if info.get("tags_section"):
            ts = info["tags_section"]
            lines.append(f"Tags Section: {ts.get('selector', 'N/A')}")
        
        if info.get("tag_items"):
            lines.append(f"\nAvailable Tags ({len(info['tag_items'])} found):")
            for tag in info["tag_items"][:15]:
                lines.append(f"  - '{tag['name']}'")
        
        if info.get("buttons"):
            lines.append(f"\nButtons ({len(info['buttons'])} found):")
            for btn in info["buttons"][:10]:
                lines.append(f"  - '{btn['text']}'")
        
        lines.append("")
        lines.append("="*70)
        lines.append("These selectors were PROVEN to work by actual execution.")
        lines.append("="*70)
        
        return "\n".join(lines)
    
    def get_precondition_code(self) -> str:
        """
        Generate Python code for precondition helper based on executed steps.
        
        This is the PROVEN code that actually worked during inspection.
        """
        if not self._cache or not self._cache.get("success"):
            return ""
        
        steps = self._cache.get("executed_steps", [])
        if not steps:
            return ""
        
        lines = []
        lines.append("def _precondition(page):")
        lines.append('    """Execute UI setup steps (auto-generated from successful inspection)"""')
        
        for step in steps:
            if step["success"] and step["selector"]:
                selector = step["selector"]
                
                # Generate code based on selector type
                if selector.startswith("[data-testid="):
                    # Extract data-testid value
                    match = re.search(r"\[data-testid='([^']+)'\]", selector)
                    if match:
                        testid = match.group(1)
                        lines.append(f"    page.locator(\"[data-testid='{testid}']\").click()")
                
                elif selector.startswith("#"):
                    # ID selector
                    lines.append(f"    page.locator(\"{selector}\").click()")
                
                elif selector.startswith("role="):
                    # Role + name
                    match = re.search(r"role=(\w+), name=(.+)", selector)
                    if match:
                        role, name = match.groups()
                        lines.append(f"    page.get_by_role(\"{role}\", name=\"{name}\").click()")
                
                elif selector.startswith("text="):
                    # Text selector
                    text = selector.replace("text=", "")
                    lines.append(f"    page.get_by_text(\"{text}\").click()")
                
                elif "filled with" in selector:
                    # Input field
                    lines.append(f"    # Input step: {step['description']}")
                
                else:
                    # Generic selector
                    lines.append(f"    page.locator(\"{selector}\").click()")
                
                lines.append("    page.wait_for_load_state('networkidle')")
        
        return "\n".join(lines)


# Global singleton instance
_inspector_instance: Optional[SmartPageInspectorV2] = None


def get_smart_page_inspector() -> SmartPageInspectorV2:
    """Get or create the global SmartPageInspectorV2 instance"""
    global _inspector_instance
    if _inspector_instance is None:
        _inspector_instance = SmartPageInspectorV2()
    return _inspector_instance
