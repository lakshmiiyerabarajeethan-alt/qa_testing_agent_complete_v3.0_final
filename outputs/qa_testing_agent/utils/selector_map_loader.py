"""
selector_map_loader.py
======================
Parses a Playwright-recorded Python script and builds a rich selector map
used by AppHelperGenerator to produce named helper functions for any app.

Previous version only matched 3 rigid patterns and missed the two most
critical selectors for Mirrix (and many real apps in general):

    MISSED:  page.locator("#rc-tabs-0-tab-filters div").filter(has_text=...).click()
    MISSED:  page.locator("a").filter(has_text="Tags").click()
    MISSED:  page.get_by_role("img", name="thumb").nth(1).click()
    MISSED:  page.get_by_text("OR", exact=True).click()

This version uses a line-by-line parser that captures ALL of:
  - get_by_role  (with .nth() / .first / exact=)
  - get_by_text  (with exact=True, .nth())
  - locator().filter(has_text=...)  — the most commonly missed pattern
  - locator().fill("value")
  - locator with .first / .nth()
  - goto()
  - Any other page.* action line

Each action gets a semantic category so the helper generator can group
them into meaningful, named functions that work for any application.
"""

import json
import os
import re
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Line parser
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_line(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("await "):
        raw = raw[len("await "):]
    if raw.endswith(";"):
        raw = raw[:-1]
    return raw.strip()


def _parse_line(raw: str) -> Optional[Dict]:
    """
    Parse a single stripped source line into an action dict.
    Returns None if the line is not a page.* action we can use.

    Every dict contains at minimum:
      raw     – original source line
      kind    – "role"|"text"|"filter_chain"|"locator"|"fill_input"|"goto"|"other"
      action  – "click"|"fill"|"press"|"goto"|"interact"
    """
    raw = _normalize_line(raw)
    if not raw.startswith("page."):
        return None

    base: Dict = {"raw": raw, "action": _detect_action(raw)}

    # goto
    m = re.match(r'page\.goto\([\'"]([^\'"]+)[\'"]\)', raw)
    if m:
        return {**base, "kind": "goto", "url": m.group(1)}

    # filter chain (JS): page.locator("sel").filter({ hasText: "Filters" })
    m = re.match(
        r'page\.locator\([\'"]([^\'"]+)[\'"]\)'
        r'(?:\.nth\(\d+\))?'
        r'\.filter\(\{\s*hasText:\s*(/[^/]+/(?:[a-z]+)?|[\'"][^\'"]+[\'"])\s*\}\)',
        raw,
    )
    if m:
        selector = m.group(1)
        raw_filt = m.group(2).strip()
        if raw_filt.startswith("/"):
            # Strip regex delimiters and anchors
            parts = raw_filt.split("/")
            if len(parts) >= 3:
                raw_filt = parts[1]
        raw_filt = raw_filt.strip("'\"")
        raw_filt = re.sub(r"^\^|\$$", "", raw_filt)
        label = re.sub(r"[\^$()?+*\\]", "", raw_filt).strip()
        return {**base, "kind": "filter_chain", "selector": selector, "filter": label}

    # filter chain: page.locator("sel").filter(has_text=<str or re.compile>)
    m = re.match(
        r'page\.locator\("([^"]+)"\)'
        r'(?:\.nth\(\d+\))?'
        r'\.filter\(has_text=(?:re\.compile\(r?"([^"]+)"\)|"([^"]+)"|\'([^\']+)\')\)',
        raw,
    )
    if m:
        selector  = m.group(1)
        raw_filt  = m.group(2) or m.group(3) or m.group(4) or ""
        label     = re.sub(r"[\^$()?+*\\]", "", raw_filt).strip()
        return {**base, "kind": "filter_chain", "selector": selector, "filter": label}

    # get_by_role (with optional .nth() / .first)
    # getByRole (JS)
    m = re.match(
        r'page\.getByRole\([\'"]([^\'"]+)[\'"]\s*,\s*\{\s*name:\s*[\'"]([^\'"]+)[\'"]',
        raw,
    )
    if m:
        return {**base, "kind": "role", "role": m.group(1), "name": m.group(2)}

    # get_by_role (with optional .nth() / .first)
    m = re.match(
        r'page\.get_by_role\([\'"]([^\'"]+)[\'"],\s*name=[\'"]([^\'"]+)[\'"]\)'
        r'(?:\.nth\(\d+\)|\.first)?',
        raw,
    )
    if m:
        return {**base, "kind": "role", "role": m.group(1), "name": m.group(2)}

    # getByText (JS) with optional exact
    m = re.match(
        r'page\.getByText\([\'"]([^\'"]+)[\'"](?:,\s*\{\s*exact:\s*(true|false)\s*\})?\)',
        raw,
    )
    if m:
        return {**base, "kind": "text", "name": m.group(1), "exact": (m.group(2) == "true")}

    # get_by_text with exact=True
    m = re.match(r'page\.get_by_text\([\'"]([^\'"]+)[\'"],\s*exact=True\)', raw)
    if m:
        return {**base, "kind": "text", "name": m.group(1), "exact": True}

    # get_by_text with optional .nth()
    m = re.match(r'page\.get_by_text\([\'"]([^\'"]+)[\'"]\)(?:\.nth\(\d+\))?', raw)
    if m:
        return {**base, "kind": "text", "name": m.group(1)}

    # locator().fill("value")
    m = re.match(r'page\.locator\([\'"]([^\'"]+)[\'"]\)\.fill\([\'"]([^\'"]*)[\'"]\)', raw)
    if m:
        return {**base, "kind": "fill_input", "selector": m.group(1), "value": m.group(2)}

    # locator with .first / .nth()
    m = re.match(r'page\.locator\([\'"]([^\'"]+)[\'"]\)(?:\.first|\.nth\(\d+\))?', raw)
    if m:
        return {**base, "kind": "locator", "selector": m.group(1)}

    # catch-all: any page.* with a recognisable action
    if any(t in raw for t in [".click(", ".fill(", ".press(", ".check(", ".select_option("]):
        return {**base, "kind": "other"}

    return None


def _detect_action(raw: str) -> str:
    if ".fill("  in raw: return "fill"
    if ".press(" in raw: return "press"
    if ".setInputFiles(" in raw: return "set_input_files"
    if ".uncheck(" in raw: return "uncheck"
    if ".click(" in raw: return "click"
    if ".check(" in raw: return "check"
    if "page.goto(" in raw: return "goto"
    return "interact"


# ─────────────────────────────────────────────────────────────────────────────
# Semantic classifier
# ─────────────────────────────────────────────────────────────────────────────

def _categorise(action: Dict) -> str:
    """
    Assign a semantic category so helpers can be grouped by purpose.

    Categories: login | navigation | filter | search | tag | asset |
                system | form | action_btn | content | other
    """
    kind       = action.get("kind", "")
    role       = action.get("role", "").lower()
    name       = action.get("name", "").lower()
    selector   = action.get("selector", "").lower()
    filt       = action.get("filter", "").lower()
    raw        = action.get("raw", "").lower()

    # login
    if any(k in name for k in ["email", "password", "username"]) and kind == "role":
        return "login"
    if role == "button" and any(k in name for k in ["login", "sign in", "log in", "sign up"]):
        return "login"

    # navigation
    if kind == "goto":
        return "navigation"
    if role == "link":
        return "navigation"

    # filter panel / section tabs (filter_chain covers RC-tabs, anchor filters, etc.)
    if kind == "filter_chain":
        return "filter"

    # search inputs and operator buttons
    if role == "textbox" and any(k in name for k in ["search", "query", "find"]):
        return "search"
    if "search" in selector or "rc_select" in selector:
        return "search"
    if kind == "text" and action.get("name", "").upper() in ("OR", "AND", "NOT"):
        return "search"

    # tag filter items: text clicks whose label ends in digits (e.g. "toys59")
    if kind == "text" and re.match(r".+\d+$", action.get("name", "")):
        return "tag"

    # asset thumbnails / detail tabs
    if role == "img" and "thumb" in name:
        return "asset"
    if role == "tab":
        return "asset"
    if role == "button" and any(k in name for k in ["preview", "close", "cancel"]):
        return "asset"

    # system utilities
    if kind == "text" and any(k in name for k in ["clear search", "clear all"]):
        return "system"
    if "clear" in raw and "search" in raw:
        return "system"

    # general action buttons
    if role == "button":
        return "action_btn"

    # form inputs
    if role in ("textbox", "checkbox", "radio", "combobox", "spinbutton"):
        return "form"
    if kind == "fill_input":
        return "form"

    # plain text / content clicks
    if kind == "text":
        return "content"

    return "other"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_selector_map_from_recording(recording_path: str) -> Dict:
    """
    Parse a Playwright recorded script and return a rich selector map dict.

    Structure:
      {
        "source":      "recorded_flow.py",
        "actions":     [ ...all unique actions... ],
        "by_category": { "filter": [...], "navigation": [...], ... }
      }
    """
    with open(recording_path, "r", encoding="utf-8") as f:
        code = f.read()

    actions: List[Dict] = []
    seen: set = set()

    for line in code.splitlines():
        stripped = line.strip()
        if stripped in seen:
            continue
        parsed = _parse_line(stripped)
        if parsed is None:
            continue
        parsed["category"] = _categorise(parsed)
        seen.add(stripped)
        actions.append(parsed)

    by_category: Dict[str, List] = {}
    for a in actions:
        by_category.setdefault(a["category"], []).append(a)

    return {
        "source": os.path.basename(recording_path),
        "actions": actions,
        "by_category": by_category,
    }


def ensure_selector_map(
    snapshot_folder: str,
    map_filename: str,
    recording_filename: str,
) -> Optional[str]:
    """
    Ensure selector_map.json exists and is up-to-date.
    Rebuilds automatically whenever recorded_flow.py is newer than the map.
    Returns the map path, or None if no files exist.
    """
    os.makedirs(snapshot_folder, exist_ok=True)
    map_path       = os.path.join(snapshot_folder, map_filename)
    recording_path = os.path.join(snapshot_folder, recording_filename)

    if not os.path.exists(recording_path):
        return map_path if os.path.exists(map_path) else None

    should_rebuild = True
    if os.path.exists(map_path):
        try:
            should_rebuild = os.path.getmtime(recording_path) > os.path.getmtime(map_path)
        except OSError:
            pass
        # Force rebuild if the map is missing expected structure (older format)
        if not should_rebuild:
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if not isinstance(existing, dict):
                    should_rebuild = True
                elif "by_category" not in existing:
                    should_rebuild = True
                else:
                    actions = existing.get("actions", []) or []
                    # Older maps used "text" instead of "name" for text actions
                    has_old_text = any(
                        a.get("kind") == "text" and "text" in a and "name" not in a
                        for a in actions
                    )
                    if has_old_text:
                        should_rebuild = True
            except Exception:
                # If we can't read/parse it, rebuild
                should_rebuild = True

    if should_rebuild:
        selector_map = build_selector_map_from_recording(recording_path)
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(selector_map, f, indent=2)

    return map_path


def load_selector_map(snapshot_folder: str, map_filename: str) -> Dict:
    """Load selector_map.json. Returns {} if the file does not exist."""
    path = os.path.join(snapshot_folder, map_filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
