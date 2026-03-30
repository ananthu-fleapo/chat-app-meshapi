"""
Unit tests for app/usage/pricing.py

Covers:
  calculate_cost — known models, unknown models, zero tokens,
                   large token counts, Decimal precision, asymmetric rates
"""

from decimal import Decimal

import pytest

from app.usage.pricing import calculate_cost


class TestCalculateCost:

    def test_known_model_returns_decimal(self):
        """Known model produces a Decimal result."""
        result = calculate_cost("openai/gpt-4o", 1000, 1000)
        assert isinstance(result, Decimal)

    def test_unknown_model_returns_none(self):
        """Model not in the pricing table returns None."""
        assert calculate_cost("unknown/model-xyz", 100, 100) is None

    def test_zero_tokens_returns_zero(self):
        """Zero prompt and completion tokens → $0.00000000."""
        result = calculate_cost("openai/gpt-4o", 0, 0)
        assert result == Decimal("0.00000000")

    def test_result_quantized_to_8_decimal_places(self):
        """Cost is always quantized to 8 decimal places."""
        result = calculate_cost("openai/gpt-4o-mini", 1, 1)
        assert result is not None
        # Exponent of the Decimal should be -8
        sign, digits, exponent = result.as_tuple()
        assert exponent == -8

    def test_gpt4o_prompt_only(self):
        """1000 prompt tokens, 0 completion → prompt cost only."""
        # gpt-4o: $0.0025 / 1k prompt
        result = calculate_cost("openai/gpt-4o", 1000, 0)
        assert result == Decimal("0.00250000")

    def test_gpt4o_completion_only(self):
        """0 prompt tokens, 1000 completion → completion cost only."""
        # gpt-4o: $0.01 / 1k completion
        result = calculate_cost("openai/gpt-4o", 0, 1000)
        assert result == Decimal("0.01000000")

    def test_gpt4o_combined(self):
        """1000 prompt + 1000 completion tokens."""
        result = calculate_cost("openai/gpt-4o", 1000, 1000)
        # 0.0025 + 0.01 = 0.0125
        assert result == Decimal("0.01250000")

    def test_asymmetric_rates_openai_o1(self):
        """o1 has very different prompt vs completion rates."""
        # o1: $0.015 / 1k prompt, $0.06 / 1k completion
        result = calculate_cost("openai/o1", 1000, 1000)
        assert result == Decimal("0.07500000")

    def test_large_token_count_no_overflow(self):
        """1 million tokens each — no float overflow or precision loss."""
        result = calculate_cost("openai/gpt-4o-mini", 1_000_000, 1_000_000)
        # $0.00015/1k * 1000 + $0.0006/1k * 1000 = 0.15 + 0.6 = 0.75
        assert result == Decimal("0.75000000")

    def test_decimal_not_float(self):
        """Result must be Decimal, not float — avoids precision accumulation errors."""
        result = calculate_cost("anthropic/claude-3-5-sonnet", 500, 500)
        assert isinstance(result, Decimal)
        assert not isinstance(result, float)

    @pytest.mark.parametrize("model,prompt,completion,expected", [
        ("openai/gpt-4o-mini",        1000, 1000, Decimal("0.00075000")),
        ("anthropic/claude-3-haiku",  1000, 1000, Decimal("0.00150000")),
        ("google/gemini-flash-1.5",   1000, 1000, Decimal("0.00037500")),
        ("deepseek/deepseek-chat",    1000, 1000, Decimal("0.00042000")),
        ("mistralai/mistral-7b-instruct", 1000, 1000, Decimal("0.00011000")),
    ])
    def test_parametrized_known_models(self, model, prompt, completion, expected):
        """Spot-check several models for correct cost computation."""
        result = calculate_cost(model, prompt, completion)
        assert result == expected

    def test_free_model_not_in_table(self):
        """Free/open-weight models not in the table return None (not zero)."""
        assert calculate_cost("meta-llama/llama-3-free", 1000, 1000) is None
