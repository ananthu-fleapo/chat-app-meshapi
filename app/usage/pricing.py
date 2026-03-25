"""
Static model pricing table.

Prices are in USD per 1 000 tokens (prompt / completion).
Source: OpenRouter model list + provider pricing pages, Q1 2026.

Phase 7 note
------------
Replace with dynamic pricing fetched from OpenRouter's /models endpoint
at startup and refreshed periodically. The calculate_cost() signature
stays identical — callers don't need to change.

Unknown models return None cost (logged but not counted toward spend cap).
"""

from decimal import Decimal

# (prompt_usd_per_1k, completion_usd_per_1k)
_PRICING: dict[str, tuple[float, float]] = {
    # ── OpenAI ────────────────────────────────────────────────────────────────
    "openai/gpt-4o":              (0.002500, 0.010000),
    "openai/gpt-4o-mini":         (0.000150, 0.000600),
    "openai/gpt-4-turbo":         (0.010000, 0.030000),
    "openai/o1":                  (0.015000, 0.060000),
    "openai/o1-mini":             (0.003000, 0.012000),
    "openai/o3-mini":             (0.001100, 0.004400),
    "openai/o3-mini-high":        (0.001100, 0.004400),
    # ── Anthropic ─────────────────────────────────────────────────────────────
    "anthropic/claude-3-5-sonnet":        (0.003000, 0.015000),
    "anthropic/claude-3-5-sonnet-20241022": (0.003000, 0.015000),
    "anthropic/claude-3-5-haiku":         (0.000800, 0.004000),
    "anthropic/claude-3-5-haiku-20241022": (0.000800, 0.004000),
    "anthropic/claude-3-opus":            (0.015000, 0.075000),
    "anthropic/claude-3-opus-20240229":   (0.015000, 0.075000),
    "anthropic/claude-3-sonnet":          (0.003000, 0.015000),
    "anthropic/claude-3-haiku":           (0.000250, 0.001250),
    # ── Google ────────────────────────────────────────────────────────────────
    "google/gemini-pro-1.5":          (0.001250, 0.005000),
    "google/gemini-flash-1.5":        (0.000075, 0.000300),
    "google/gemini-flash-1.5-8b":     (0.0000375, 0.000150),
    "google/gemini-2.0-flash":        (0.000100, 0.000400),
    "google/gemini-2.0-flash-lite":   (0.000075, 0.000300),
    # ── Meta / Llama ──────────────────────────────────────────────────────────
    "meta-llama/llama-3.1-8b-instruct":  (0.000055, 0.000055),
    "meta-llama/llama-3.1-70b-instruct": (0.000350, 0.000400),
    "meta-llama/llama-3.3-70b-instruct": (0.000350, 0.000400),
    "meta-llama/llama-3.1-405b-instruct": (0.002700, 0.002700),
    # ── Mistral ───────────────────────────────────────────────────────────────
    "mistralai/mistral-7b-instruct":  (0.000055, 0.000055),
    "mistralai/mistral-small":        (0.000100, 0.000300),
    "mistralai/mistral-large":        (0.002000, 0.006000),
    "mistralai/mixtral-8x7b-instruct": (0.000240, 0.000240),
    # ── DeepSeek ──────────────────────────────────────────────────────────────
    "deepseek/deepseek-chat":    (0.000140, 0.000280),
    "deepseek/deepseek-r1":      (0.000550, 0.002190),
    # ── Cohere ────────────────────────────────────────────────────────────────
    "cohere/command-r":          (0.000500, 0.001500),
    "cohere/command-r-plus":     (0.003000, 0.015000),
    # ── Perplexity ────────────────────────────────────────────────────────────
    "perplexity/sonar":          (0.001000, 0.001000),
    "perplexity/sonar-pro":      (0.003000, 0.015000),
}


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal | None:
    """
    Return the USD cost for a completion, or None if the model is unknown.

    Uses Decimal arithmetic to avoid float precision loss when summing
    costs across many events for spend cap checks.
    """
    pricing = _PRICING.get(model)
    if pricing is None:
        return None

    prompt_cost = Decimal(str(pricing[0])) * prompt_tokens / 1000
    completion_cost = Decimal(str(pricing[1])) * completion_tokens / 1000
    return (prompt_cost + completion_cost).quantize(Decimal("0.00000001"))
