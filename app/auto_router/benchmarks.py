"""
Benchmark-based candidate ranking for the Auto Router.

Ported from service/src/utils/ai-benchmarks.ts.

Each entry in SUPERMODE_BENCHMARKS maps a task category to an ordered list of
model brands.  Ties share a sub-list.  Earlier position = better benchmark rank.

Usage: call build_benchmark_hint(candidates) to get a compact hint string that
can be appended to the classifier prompt so the LLM knows which brands excel at
which task types.
"""

from __future__ import annotations

import random

# fmt: off
SUPERMODE_BENCHMARKS: dict[str, list[str | list[str]]] = {
    "File generation - pdf, docx, pptx, excel": [
        "claude", ["gemini"],
    ],
    "Creative writing / storytelling - Long-form coherence": [
        "claude", ["chatgpt", "gemini"], "moonshot", "grok", "qwen", "perplexity", "deepseek", "mistral",
    ],
    "Creative writing / storytelling - Voice mimicry / style control": [
        "claude", "grok", "chatgpt", "gemini", "bytedance", "qwen", "moonshot", "perplexity", "deepseek", "mistral",
    ],
    "Creative writing / storytelling - Character & world consistency": [
        "claude", ["gemini", "chatgpt"], "moonshot", "bytedance", "grok", "qwen", "perplexity", "deepseek", "mistral",
    ],
    "Creative writing / storytelling - Instruction adherence": [
        "claude", "deepseek", "chatgpt", "gemini", "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Creative writing / storytelling- Revision quality": [
        "claude", "chatgpt", "gemini", "moonshot", "qwen", "grok", "deepseek", "bytedance", "perplexity", "mistral",
    ],
    "General reasoning / Q&A - General Conversation, Chatting": [
        ["claude", "deepseek", "chatgpt", "gemini", "grok", "mistral"], "qwen", "moonshot", "perplexity",
    ],
    "General reasoning / Q&A - Closed-book factuality": [
        ["deepseek", "gemini"], ["claude", "chatgpt"], "qwen", "moonshot", "grok", "perplexity", "bytedance", "mistral",
    ],
    "General reasoning / Q&A - Decomposition / step-planning": [
        ["gemini", "deepseek"], "chatgpt", "claude", "moonshot", "qwen", "grok", "perplexity", "mistral", "bytedance",
    ],
    "General reasoning / Q&A - Numerical reliability": [
        "deepseek", ["moonshot", "chatgpt"], "claude", ["qwen", "gemini"], "grok", "bytedance", "perplexity", "mistral",
    ],
    "General reasoning / Q&A - Ambiguity handling": [
        ["chatgpt", "gemini"], "claude", "moonshot", "qwen", "deepseek", "grok", "perplexity", "mistral", "bytedance",
    ],
    "General reasoning / Q&A - Uncertainty calibration": [
        "chatgpt", "gemini", "claude", "moonshot", "qwen", "deepseek", "perplexity", "grok", "mistral", "bytedance",
    ],
    "Coding - Bug localization & debugging": [
        ["chatgpt", "claude"], ["deepseek", "gemini"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Coding - Repo comprehension (architecture)": [
        ["deepseek", "gemini"], ["chatgpt", "claude"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Coding - Feature scaffolding (greenfield)": [
        ["chatgpt", "claude"], ["deepseek", "gemini"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Coding - Migration / translation": [
        ["chatgpt", "claude"], ["deepseek", "gemini"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Coding - Test generation & CI scaffolds": [
        ["chatgpt", "claude"], ["deepseek", "gemini"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Coding - Algorithmic / competitive programming": [
        ["chatgpt", "claude"], ["deepseek", "gemini"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Coding - Data/ML notebooks (pandas/NumPy/Torch)": [
        ["deepseek", "gemini"], ["chatgpt", "claude"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Coding - Constrained output (AST/diff/JSON-only)": [
        ["chatgpt", "claude"], ["deepseek", "gemini"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Coding - Agentic build-run-fix loops": [
        ["chatgpt", "claude"], ["deepseek", "gemini"], "qwen", "moonshot", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Math / logic - Arithmetic & word problems": [
        "deepseek", "chatgpt", "claude", "qwen", "moonshot", "gemini", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Math / logic - Symbolic algebra": [
        "deepseek", "qwen", "chatgpt", "claude", "moonshot", "gemini", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Math / logic - Combinatorics / graph reasoning": [
        "deepseek", "chatgpt", "claude", "qwen", "moonshot", "gemini", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Math / logic - Proof-like explanations": [
        "deepseek", "chatgpt", "claude", "qwen", "moonshot", "gemini", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Multimodal - OCR & document QA": [
        "gemini", ["chatgpt", "claude"], "qwen", "moonshot", "deepseek", "perplexity", "bytedance", "grok", "mistral",
    ],
    "Multimodal - Chart/table reasoning": [
        "gemini", ["chatgpt", "claude", "qwen"], "moonshot", "deepseek", "perplexity", "grok", "mistral", "bytedance",
    ],
    "Multimodal - UI → code (from screenshot)": [
        "gemini", "chatgpt", "grok", "claude", "moonshot", "qwen", "deepseek", "perplexity", "mistral", "bytedance",
    ],
    "Multimodal - Image grounding & captions": [
        "gemini", "chatgpt", "claude", "qwen", "moonshot", "deepseek", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Multimodal - Long-video understanding": [
        "gemini", "chatgpt", "claude", "qwen", "moonshot", "deepseek", "grok", "perplexity", "mistral", "bytedance",
    ],
    "Safety / compliance - Refusal precision": [
        "claude", "chatgpt", "gemini", "perplexity", "qwen", "moonshot", "deepseek", "grok", "mistral", "bytedance",
    ],
    "Safety / compliance - Jailbreak resistance": [
        "claude", "chatgpt", "gemini", "perplexity", "qwen", "moonshot", "deepseek", "grok", "mistral", "bytedance",
    ],
    "Safety / compliance - PII & privacy handling": [
        "claude", "chatgpt", "gemini", "perplexity", "qwen", "moonshot", "deepseek", "grok", "mistral", "bytedance",
    ],
    "Safety / compliance - Policy following": [
        "claude", "chatgpt", "gemini", "perplexity", "qwen", "moonshot", "deepseek", "grok", "mistral", "bytedance",
    ],
    "Web research / citations - Citation precision": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Web research / citations - Recall / breadth": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Web research / citations - Quote fidelity": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Web research / citations - Freshness (recency)": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Web research / citations - Inline code-check / quick run": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Web research / citations - News": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Web research / citations - Recent Topics/Latest Information": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Web research / citations - currency": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Web research / citations - time": [
        ["chatgpt", "gemini", "claude", "grok"], "deepseek", "moonshot", "mistral", "bytedance", "perplexity", "qwen",
    ],
    "Conversational tone / style - Persona control": [
        "claude", "chatgpt", "grok", "gemini", "moonshot", "qwen", "deepseek", "perplexity", "mistral", "bytedance",
    ],
    "Conversational tone / style - Empathy & prosody": [
        ["claude", "gemini"], "chatgpt", "grok", "moonshot", "qwen", "deepseek", "bytedance", "perplexity", "mistral",
    ],
    "Conversational tone / style - Humor / wit": [
        ["claude", "grok"], ["chatgpt", "gemini", "moonshot", "deepseek"], "qwen", "perplexity", "bytedance", "mistral",
    ],
    "Conversational tone / style - Contextual memory (short-term)": [
        ["gemini", "claude"], ["chatgpt", "moonshot"], "deepseek", "qwen", "grok", "perplexity", "bytedance", "mistral",
    ],
    "Conversational tone / style - Long-term persona persistence": [
        ["gemini", "claude"], "chatgpt", "moonshot", "deepseek", "qwen", "grok", "perplexity", "mistral", "bytedance",
    ],
}
# fmt: on

SUPERMODE_CATEGORIES = list(SUPERMODE_BENCHMARKS.keys())

# ── Brand → model ID mappings ─────────────────────────────────────────────────
# Source: SUPERMODE_VERSIONS in service/src/utils/ai-models.ts
# Provider prefixes are the routersvc gateway prefixes (not bare model names).

# Update values here when a better premium model version becomes available.
BENCHMARK_BRAND_TO_PREMIUM_MODEL_ID: dict[str, str] = {
    "chatgpt": "openai/gpt-5.4",
    "claude": "anthropic/claude-sonnet-4-6",
    "gemini": "google/gemini-3.1-pro-preview",  # openrouter
    "deepseek": "deepseek/deepseek-r1",
    "grok": "x-ai/grok-4",  # openrouter
    "perplexity": "perplexity/sonar-pro",  # openrouter
    "mistral": "mistralai/mistral-medium-3.1",  # openrouter
    "qwen": "qwen/qwen3-max",
    "moonshot": "moonshotai/kimi-k2-thinking",
    "bytedance": "bytedance-seed/seed-2.0-lite",
}

# Update values here when a better standard model version becomes available.
BENCHMARK_BRAND_TO_STANDARD_MODEL_ID: dict[str, str] = {
    "chatgpt": "openai/gpt-5.4-mini",
    "claude": "anthropic/claude-haiku-4.5",
    "gemini": "google/gemini-3-flash-preview",
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "grok": "x-ai/grok-4.1-fast",
    "perplexity": "perplexity/sonar",
    "mistral": "mistralai/mistral-medium-3.1",
    "qwen": "qwen/qwen-flash",
    "moonshot": "moonshotai/kimi-k2.5",
    "bytedance": "bytedance-seed/seed-2.0-mini",
}

BENCHMARK_BRAND_RESPONSES_API_SUPPORTED_STANDARD = {
    "chatgpt": "openai/gpt-5.4-mini",
    "qwen": "qwen/qwen-flash",
}

BENCHMARK_BRAND_RESPONSES_API_SUPPORTED_PREMIUM = {
    "chatgpt": "openai/gpt-5.4",
    "qwen": "qwen/qwen3-max",
}

# Inverted maps: model_id → brand, built once at import time.
_MODEL_ID_TO_BRAND: dict[str, str] = {
    **{v: k for k, v in BENCHMARK_BRAND_TO_PREMIUM_MODEL_ID.items()},
    **{v: k for k, v in BENCHMARK_BRAND_TO_STANDARD_MODEL_ID.items()},
}

# Provider prefix → brand for fallback prefix matching (derived from premium mapping).
_PREFIX_TO_BRAND: dict[str, str] = {
    v.split("/")[0] + "/": k for k, v in BENCHMARK_BRAND_TO_PREMIUM_MODEL_ID.items()
}

# Brand to use when category is unknown or all brands are unmapped.
DEFAULT_FALLBACK_BRAND = "chatgpt"


def _candidate_brand(model_id: str) -> str | None:
    """Return the benchmark brand name for a model ID, or None if unknown.

    Exact match first (covers both tiers), then provider-prefix fallback.
    """
    brand = _MODEL_ID_TO_BRAND.get(model_id)
    if brand:
        return brand
    lower = model_id.lower()
    for prefix, b in _PREFIX_TO_BRAND.items():
        if lower.startswith(prefix):
            return b
    return None


def resolve_from_benchmark_category(
    category: str,
    mode: str = "premium",
    supermode_index: int = 0,
    responses_api: bool = False,
) -> str | None:
    """
    Given a classified CATEGORY, MODE, and supermode_index, return a model ID.

    When responses_api=True, walks the full ranking in order and returns the first
    brand that appears in BENCHMARK_BRAND_RESPONSES_API_SUPPORTED_*. Returns None
    if no responses-capable brand exists in the ranking (caller falls back to default).

    Mirrors getModelsFromClassification() in service/src/chat/model-classifier.service.ts:
      1. Look up SUPERMODE_BENCHMARKS[category]; use DEFAULT_FALLBACK_BRAND if missing.
      2. Select tier entry: ranking[supermode_index % len(ranking)].
         supermode_index=0 always picks the best (tier-1) entry.
      3. String entry → return its mapped model ID directly.
      4. Tie-list entry → filter to brands present in the mapping, pick one at random
         (matches the `sample(candidates)` behaviour in the TS implementation).
      5. Unknown mode defaults to premium.
    """
    if responses_api:
        responses_mapping = (
            BENCHMARK_BRAND_RESPONSES_API_SUPPORTED_STANDARD
            if mode == "standard"
            else BENCHMARK_BRAND_RESPONSES_API_SUPPORTED_PREMIUM
        )
        ranking = SUPERMODE_BENCHMARKS.get(category, [])
        for entry in ranking:
            brands = [entry] if isinstance(entry, str) else entry
            for brand in brands:
                if brand in responses_mapping:
                    return responses_mapping[brand]
        return None

    mapping = (
        BENCHMARK_BRAND_TO_STANDARD_MODEL_ID
        if mode == "standard"
        else BENCHMARK_BRAND_TO_PREMIUM_MODEL_ID
    )

    ranking = SUPERMODE_BENCHMARKS.get(category)
    if not ranking:
        return mapping.get(DEFAULT_FALLBACK_BRAND)

    selected = ranking[supermode_index % len(ranking)]

    if isinstance(selected, str):
        return mapping.get(selected) or mapping.get(DEFAULT_FALLBACK_BRAND)

    # Tie-list: filter to brands that have a mapping, then pick at random.
    candidates = [brand for brand in selected if brand in mapping]
    if not candidates:
        return mapping.get(DEFAULT_FALLBACK_BRAND)
    return mapping[random.choice(candidates)]
