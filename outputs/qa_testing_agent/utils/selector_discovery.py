"""
Smart Selector Discovery - Uses Playwright's intelligent element discovery.

This module tries multiple strategies to find elements, similar to how
Playwright Codegen works. It prioritizes the most reliable selectors.

Strategy order:
1. data-testid (most reliable, survives refactoring)
2. ID (reliable, but can change)
3. aria-label (accessible, semantic)
4. role + name (semantic HTML)
5. placeholder (for inputs)
6. text content (least reliable, but works)
7. CSS selector (fallback)
"""
import logging
import re
from typing import Optional, Dict, List, Tuple
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class SmartSelectorDiscovery:
    """
    Discovers the best selector for an element using multiple strategies.
    
    Similar to Playwright Codegen, but automated and integrated into the pipeline.
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.timeout = 5000  # 5 seconds for discovery attempts
    
    def find_and_click(self, description: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Find an element based on natural language description and click it.
        
        Args:
            description: Natural language like "Click Filter" or "Expand Tags"
            
        Returns:
            Tuple of (success, selector_used, element_info)
            
        Examples:
            "Click Filter" → finds button/link/div with text "Filter"
            "Expand Tags" → finds element with text "Tags"
            "Type xyz into search" → finds input and types
        """
        # Parse the description
        action, target = self._parse_description(description)
        
        logger.info(f"Finding element: action='{action}', target='{target}'")
        
        if action == "click":
            return self._find_and_click_element(target)
        elif action == "type":
            return self._find_and_type(target, description)
        elif action == "expand":
            return self._find_and_expand(target)
        else:
            # Generic click
            return self._find_and_click_element(target)
    
    def _parse_description(self, description: str) -> Tuple[str, str]:
        """Parse natural language description into action and target."""
        desc_lower = description.lower().strip()
        
        # Extract action
        if any(word in desc_lower for word in ["type", "enter", "input", "fill"]):
            action = "type"
            # Extract what to type
            match = re.search(r"(?:type|enter|input|fill)\s+['\"]?(\w+)['\"]?", desc_lower)
            target = match.group(1) if match else ""
        elif any(word in desc_lower for word in ["expand", "open", "show"]):
            action = "expand"
            # Extract what to expand (remove action words)
            target = re.sub(r"^(expand|open|show)\s+", "", desc_lower, flags=re.IGNORECASE).strip()
        else:
            action = "click"
            # Extract what to click (remove action words)
            target = re.sub(r"^(click|press|tap|select)\s+", "", desc_lower, flags=re.IGNORECASE).strip()
        
        return action, target
    
    def _find_and_click_element(self, target: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Find and click an element using multiple strategies."""
        
        # Strategy 1: Try data-testid
        selector, info = self._try_data_testid(target)
        if selector:
            return True, selector, info
        
        # Strategy 2: Try ID
        selector, info = self._try_id(target)
        if selector:
            return True, selector, info
        
        # Strategy 3: Try aria-label
        selector, info = self._try_aria_label(target)
        if selector:
            return True, selector, info
        
        # Strategy 4: Try role + name (button, link, etc)
        selector, info = self._try_role_name(target)
        if selector:
            return True, selector, info

        # Strategy 5: RC-tabs / Ant Design tab pattern  
        # Recordings show: page.locator("#rc-tabs-0-tab-filters div").filter(...)
        selector, info = self._try_rc_tabs(target)
        if selector:
            return True, selector, info

        # Strategy 6: Anchor / sidebar filter link  
        # Recordings show: page.locator("a").filter(has_text="Tags").click()
        selector, info = self._try_anchor_filter(target)
        if selector:
            return True, selector, info
        
        # Strategy 7: Try text content
        selector, info = self._try_text(target)
        if selector:
            return True, selector, info
        
        # Strategy 8: Try partial text match
        selector, info = self._try_partial_text(target)
        if selector:
            return True, selector, info
        
        logger.warning(f"Could not find element for: {target}")
        return False, None, None

    def _try_rc_tabs(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """
        RC-tabs / Ant Design tab pattern.
        e.g. page.locator("#rc-tabs-0-tab-filters div").filter(has_text="Filters")
        Also tries generic [role=tab] with has_text filter.
        """
        slug = target.lower().replace(" ", "-")
        id_patterns = [
            f"[id*='tab-{slug}']",
            f"[id*='{slug}']",
        ]
        for css in id_patterns:
            try:
                locator = self.page.locator(css).filter(
                    has_text=re.compile(f"^{re.escape(target)}$", re.IGNORECASE)
                ).first
                if locator.is_visible(timeout=self.timeout):
                    locator.click()
                    logger.info(f"✓ Found via RC-tabs id: {css}")
                    return css, f"rc-tabs:{target}"
            except Exception:
                continue

        # Generic role=tab with text filter
        try:
            locator = self.page.locator("[role='tab']").filter(
                has_text=re.compile(f"^{re.escape(target)}$", re.IGNORECASE)
            ).first
            if locator.is_visible(timeout=self.timeout):
                locator.click()
                logger.info(f"✓ Found via role=tab filter: {target}")
                return f"[role='tab']:has-text('{target}')", f"role=tab:{target}"
        except Exception:
            pass

        return None, None

    def _try_anchor_filter(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Anchor / sidebar filter link pattern.
        e.g. page.locator("a").filter(has_text="Tags").click()
        Tries <a>, <div>, <span>, <li> elements with exact text match.
        """
        pattern = re.compile(f"^{re.escape(target)}$", re.IGNORECASE)
        for tag in ["a", "div", "span", "li"]:
            try:
                locator = self.page.locator(tag).filter(has_text=pattern).first
                if locator.is_visible(timeout=self.timeout):
                    locator.click()
                    logger.info(f"✓ Found via <{tag}> filter: {target}")
                    return f"{tag}:has-text('{target}')", f"{tag}:{target}"
            except Exception:
                continue
        return None, None

    
    def _try_data_testid(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """Try finding by data-testid attribute."""
        # Common patterns
        patterns = [
            target.lower().replace(" ", "-"),
            target.lower().replace(" ", "_"),
            f"{target.lower()}-button",
            f"{target.lower()}-btn",
            target.lower(),
        ]
        
        for pattern in patterns:
            try:
                locator = self.page.locator(f"[data-testid='{pattern}']").first
                if locator.is_visible(timeout=self.timeout):
                    locator.click()
                    selector = f"[data-testid='{pattern}']"
                    logger.info(f"✓ Found via data-testid: {selector}")
                    return selector, f"data-testid={pattern}"
            except:
                continue
        
        return None, None
    
    def _try_id(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """Try finding by ID attribute."""
        patterns = [
            target.lower().replace(" ", "-"),
            target.lower().replace(" ", "_"),
            target.lower(),
        ]
        
        for pattern in patterns:
            try:
                locator = self.page.locator(f"#{pattern}").first
                if locator.is_visible(timeout=self.timeout):
                    locator.click()
                    selector = f"#{pattern}"
                    logger.info(f"✓ Found via ID: {selector}")
                    return selector, f"id={pattern}"
            except:
                continue
        
        return None, None
    
    def _try_aria_label(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """Try finding by aria-label."""
        try:
            # Exact match
            locator = self.page.get_by_label(target, exact=True).first
            if locator.is_visible(timeout=self.timeout):
                locator.click()
                selector = f"[aria-label='{target}']"
                logger.info(f"✓ Found via aria-label: {selector}")
                return selector, f"aria-label={target}"
        except:
            pass
        
        try:
            # Partial match
            locator = self.page.get_by_label(re.compile(target, re.IGNORECASE)).first
            if locator.is_visible(timeout=self.timeout):
                locator.click()
                aria_label = locator.get_attribute("aria-label")
                selector = f"[aria-label='{aria_label}']"
                logger.info(f"✓ Found via aria-label (partial): {selector}")
                return selector, f"aria-label={aria_label}"
        except:
            pass
        
        return None, None
    
    def _try_role_name(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """Try finding by role and name (button, link, etc)."""
        roles = ["button", "link", "tab", "menuitem", "option"]
        
        for role in roles:
            try:
                # Exact match
                locator = self.page.get_by_role(role, name=target, exact=False).first
                if locator.is_visible(timeout=self.timeout):
                    locator.click()
                    selector = f"role={role}, name={target}"
                    logger.info(f"✓ Found via role+name: {selector}")
                    return selector, f"role={role}, name={target}"
            except:
                continue
            
            try:
                # Regex match
                locator = self.page.get_by_role(role, name=re.compile(target, re.IGNORECASE)).first
                if locator.is_visible(timeout=self.timeout):
                    locator.click()
                    text = locator.inner_text()
                    selector = f"role={role}, name={text}"
                    logger.info(f"✓ Found via role+name (regex): {selector}")
                    return selector, f"role={role}, name={text}"
            except:
                continue
        
        return None, None
    
    def _try_text(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """Try finding by exact text content."""
        try:
            locator = self.page.get_by_text(target, exact=True).first
            if locator.is_visible(timeout=self.timeout):
                locator.click()
                selector = f"text={target}"
                logger.info(f"✓ Found via text (exact): {selector}")
                return selector, f"text={target}"
        except:
            pass
        
        return None, None
    
    def _try_partial_text(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        """Try finding by partial text match."""
        try:
            locator = self.page.get_by_text(re.compile(target, re.IGNORECASE)).first
            if locator.is_visible(timeout=self.timeout):
                locator.click()
                text = locator.inner_text()
                selector = f"text={text}"
                logger.info(f"✓ Found via text (partial): {selector}")
                return selector, f"text={text}"
        except:
            pass
        
        return None, None
    
    def _find_and_type(self, target: str, full_description: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Find input field and type text."""
        # Extract what to type
        match = re.search(r"['\"]([^'\"]+)['\"]|type\s+(\w+)", full_description.lower())
        text_to_type = match.group(1) or match.group(2) if match else target
        
        # Try finding input by placeholder, label, or role
        strategies = [
            lambda: self.page.get_by_placeholder(re.compile(target, re.IGNORECASE)).first,
            lambda: self.page.get_by_label(re.compile(target, re.IGNORECASE)).first,
            lambda: self.page.get_by_role("textbox", name=re.compile(target, re.IGNORECASE)).first,
        ]
        
        for strategy in strategies:
            try:
                locator = strategy()
                if locator.is_visible(timeout=self.timeout):
                    locator.fill(text_to_type)
                    logger.info(f"✓ Typed '{text_to_type}' into input")
                    return True, f"input (filled with {text_to_type})", f"input: {target}"
            except:
                continue
        
        return False, None, None
    
    def _find_and_expand(self, target: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Find and expand a collapsible section."""
        # Try various strategies for expandable elements
        # Often they're buttons or divs with specific attributes
        
        # Strategy 1: Look for aria-expanded=false
        try:
            locator = self.page.locator(f"[aria-expanded='false']:has-text('{target}')").first
            if locator.is_visible(timeout=self.timeout):
                locator.click()
                logger.info(f"✓ Expanded via aria-expanded: {target}")
                return True, f"[aria-expanded='false']:has-text('{target}')", f"expanded {target}"
        except:
            pass
        
        # Strategy 2: Just click the text (often works for accordions)
        return self._find_and_click_element(target)