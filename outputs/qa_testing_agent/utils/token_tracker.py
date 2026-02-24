"""
utils/token_tracker.py - Token usage tracker for all OpenAI API calls.

Tracks prompt, completion, and total tokens per agent across an entire
pipeline run. Import `token_tracker` (the global singleton) anywhere,
call .record() after each API call, and call .print_summary() / .to_dict()
at the end of the run.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# GPT-4o pricing per 1M tokens (update if OpenAI changes rates)
_PRICE_PER_1M = {
    "gpt-4o":            {"prompt": 2.50,  "completion": 10.00},
    "gpt-4o-mini":       {"prompt": 0.15,  "completion": 0.60},
    "gpt-4-turbo":       {"prompt": 10.00, "completion": 30.00},
    "gpt-3.5-turbo":     {"prompt": 0.50,  "completion": 1.50},
}
_DEFAULT_PRICE = {"prompt": 2.50, "completion": 10.00}  # fallback = gpt-4o


@dataclass
class AgentTokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    models_used: Dict[str, int] = field(default_factory=dict)  # model → call count

    def add(self, prompt: int, completion: int, total: int, model: str = ""):
        self.prompt_tokens     += prompt
        self.completion_tokens += completion
        self.total_tokens      += total
        self.call_count        += 1
        if model:
            self.models_used[model] = self.models_used.get(model, 0) + 1

    def estimated_cost(self, model: str = "gpt-4o") -> float:
        # Use the first model seen if available
        if self.models_used:
            model = next(iter(self.models_used))
        # Normalise "gpt-4o-2024-..." → "gpt-4o" etc.
        for key in _PRICE_PER_1M:
            if model.startswith(key):
                prices = _PRICE_PER_1M[key]
                break
        else:
            prices = _DEFAULT_PRICE
        return (self.prompt_tokens / 1_000_000 * prices["prompt"] +
                self.completion_tokens / 1_000_000 * prices["completion"])


class TokenTracker:
    """
    Global tracker for OpenAI token usage across all agents.

    Usage
    -----
    from utils.token_tracker import token_tracker

    response = client.chat.completions.create(...)
    token_tracker.record("MyAgent", response)

    # At end of pipeline:
    token_tracker.print_summary()
    """

    def __init__(self):
        self._usage: Dict[str, AgentTokenUsage] = {}
        self._default_model: str = "gpt-4o"

    def reset(self):
        """Clear all recorded usage (call at the start of each pipeline run)."""
        self._usage = {}

    def record(self, agent_name: str, response, model: str = ""):
        """
        Record token usage from an OpenAI ChatCompletion response.

        Args:
            agent_name: Human-readable name shown in the summary table.
            response:   The raw response object from client.chat.completions.create().
            model:      Model string (auto-read from response if omitted).
        """
        usage = getattr(response, "usage", None)
        if not usage:
            logger.warning(f"[token_tracker] No usage data in response for {agent_name}")
            return

        # Try to get model from the response object itself
        if not model:
            model = getattr(response, "model", self._default_model) or self._default_model

        prompt     = getattr(usage, "prompt_tokens", 0) or 0
        completion = getattr(usage, "completion_tokens", 0) or 0
        total      = getattr(usage, "total_tokens", 0) or 0

        if agent_name not in self._usage:
            self._usage[agent_name] = AgentTokenUsage()

        self._usage[agent_name].add(prompt, completion, total, model)

        logger.debug(
            f"[tokens] {agent_name:30s} | "
            f"prompt={prompt:6d}  completion={completion:6d}  total={total:6d}"
        )

    def summary(self) -> Dict[str, AgentTokenUsage]:
        """Return the raw per-agent usage dict."""
        return dict(self._usage)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable summary dict."""
        result = {"agents": {}, "totals": {}, "estimated_cost_usd": 0.0}
        grand = AgentTokenUsage()

        for name, u in self._usage.items():
            result["agents"][name] = {
                "calls": u.call_count,
                "prompt_tokens": u.prompt_tokens,
                "completion_tokens": u.completion_tokens,
                "total_tokens": u.total_tokens,
                "estimated_cost_usd": round(u.estimated_cost(), 6),
            }
            grand.add(u.prompt_tokens, u.completion_tokens, u.total_tokens)

        result["totals"] = {
            "calls": grand.call_count,
            "prompt_tokens": grand.prompt_tokens,
            "completion_tokens": grand.completion_tokens,
            "total_tokens": grand.total_tokens,
        }
        result["estimated_cost_usd"] = round(grand.estimated_cost(), 6)
        return result

    def print_summary(self):
        """Print a formatted token usage table to stdout / log."""
        if not self._usage:
            logger.info("[token_tracker] No token usage recorded for this run.")
            return

        col = 32  # agent name column width
        header = (f"\n{'=' * 72}\n"
                  f"  TOKEN USAGE SUMMARY\n"
                  f"{'=' * 72}\n"
                  f"  {'AGENT':<{col}} {'CALLS':>5} {'PROMPT':>9} {'COMPL':>9} {'TOTAL':>9}  {'COST':>8}\n"
                  f"  {'-' * (col + 47)}")
        print(header)
        logger.info(header)

        grand = AgentTokenUsage()
        for name, u in self._usage.items():
            cost = u.estimated_cost()
            line = (f"  {name:<{col}} {u.call_count:>5} "
                    f"{u.prompt_tokens:>9,} {u.completion_tokens:>9,} "
                    f"{u.total_tokens:>9,}  ${cost:>7.4f}")
            print(line)
            logger.info(line)
            grand.add(u.prompt_tokens, u.completion_tokens, u.total_tokens)

        total_cost = grand.estimated_cost()
        footer = (f"  {'-' * (col + 47)}\n"
                  f"  {'TOTAL':<{col}} {grand.call_count:>5} "
                  f"{grand.prompt_tokens:>9,} {grand.completion_tokens:>9,} "
                  f"{grand.total_tokens:>9,}  ${total_cost:>7.4f}\n"
                  f"{'=' * 72}\n"
                  f"  Prices: gpt-4o $2.50/1M prompt · $10.00/1M completion (est.)\n"
                  f"{'=' * 72}\n")
        print(footer)
        logger.info(footer)


# ---------------------------------------------------------------------------
# Global singleton — import this in every agent and in main.py
# ---------------------------------------------------------------------------
token_tracker = TokenTracker()
