"""
Unit tests for app/usage/balance.py

Covers:
  check_balance  — free model bypass, paid model pass/block, unknown model
  deduct_balance — happy path, zero cost skip, DB error swallowed
  credit_balance — new user insert, existing user increment
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_execute_result


# ── check_balance ─────────────────────────────────────────────────────────────

class TestCheckBalance:

    async def test_free_model_skips_balance_check(self, mock_db):
        """Free model always passes regardless of balance."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        # model_prices row: is_free = True
        mock_db.execute.return_value = make_execute_result(rows=[(True,)])

        # Should not raise even though we never query user_balances
        await check_balance("user-123", "meta-llama/llama-3-free", mock_db)

        # Only one execute call — balance was never queried
        assert mock_db.execute.call_count == 1

    async def test_paid_model_with_positive_balance_passes(self, mock_db):
        """Paid model with balance > 0 proceeds."""
        from app.usage.balance import check_balance

        # First call: model_prices → is_free = False
        # Second call: user_balances → balance = 5.00
        mock_db.execute.side_effect = [
            make_execute_result(rows=[(False,)]),
            make_execute_result(rows=[(Decimal("5.000000"),)]),
        ]

        await check_balance("user-123", "openai/gpt-4o", mock_db)  # no exception

    async def test_paid_model_with_zero_balance_raises_402(self, mock_db):
        """Paid model with balance = 0 → PaymentRequiredError."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(False,)]),
            make_execute_result(rows=[(Decimal("0"),)]),
        ]

        with pytest.raises(PaymentRequiredError):
            await check_balance("user-123", "openai/gpt-4o", mock_db)

    async def test_paid_model_with_negative_balance_raises_402(self, mock_db):
        """Balance that went slightly negative (post-deduction overshoot) still blocks."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(False,)]),
            make_execute_result(rows=[(Decimal("-0.000500"),)]),
        ]

        with pytest.raises(PaymentRequiredError):
            await check_balance("user-123", "openai/gpt-4o", mock_db)

    async def test_unknown_model_treated_as_paid(self, mock_db):
        """Model not in model_prices defaults to paid — requires balance."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(rows=None),               # model not found
            make_execute_result(rows=[(Decimal("0"),)]),  # zero balance
        ]

        with pytest.raises(PaymentRequiredError):
            await check_balance("user-123", "unknown/model-x", mock_db)

    async def test_unknown_model_with_positive_balance_passes(self, mock_db):
        """Unknown model + positive balance → allowed."""
        from app.usage.balance import check_balance

        mock_db.execute.side_effect = [
            make_execute_result(rows=None),
            make_execute_result(rows=[(Decimal("10.00"),)]),
        ]

        await check_balance("user-123", "unknown/model-x", mock_db)

    async def test_no_balance_row_treated_as_zero(self, mock_db):
        """User with no balance row → treated as $0 → blocked for paid model."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(False,)]),  # paid model
            make_execute_result(rows=None),         # no balance row
        ]

        with pytest.raises(PaymentRequiredError):
            await check_balance("new-user", "openai/gpt-4o", mock_db)

    async def test_error_message_mentions_top_up(self, mock_db):
        """402 error message should guide the user."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(False,)]),
            make_execute_result(rows=[(Decimal("0"),)]),
        ]

        with pytest.raises(PaymentRequiredError) as exc_info:
            await check_balance("user-123", "openai/gpt-4o", mock_db)

        assert "balance" in exc_info.value.message.lower()


# ── deduct_balance ────────────────────────────────────────────────────────────

class TestDeductBalance:

    async def test_deducts_cost_from_balance(self):
        """Happy path: issues UPDATE with correct values."""
        from app.usage.balance import deduct_balance

        mock_session = AsyncMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.usage.balance.get_session_factory") as mock_factory:
            mock_factory.return_value.return_value = mock_cm
            await deduct_balance("user-123", Decimal("0.00150000"))

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify the UPDATE was called with the right cost and owner
        call_kwargs = mock_session.execute.call_args[0][1]
        assert call_kwargs["cost"] == Decimal("0.00150000")
        assert call_kwargs["owner"] == "user-123"

    async def test_zero_cost_skips_update(self):
        """Cost of zero should not issue any DB query."""
        from app.usage.balance import deduct_balance

        with patch("app.usage.balance.get_session_factory") as mock_factory:
            await deduct_balance("user-123", Decimal("0"))
            mock_factory.assert_not_called()

    async def test_negative_cost_skips_update(self):
        """Negative cost should not issue any DB query."""
        from app.usage.balance import deduct_balance

        with patch("app.usage.balance.get_session_factory") as mock_factory:
            await deduct_balance("user-123", Decimal("-0.001"))
            mock_factory.assert_not_called()

    async def test_db_error_is_swallowed(self):
        """DB failure must never propagate — response has already been sent."""
        from app.usage.balance import deduct_balance

        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("connection lost")
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.usage.balance.get_session_factory") as mock_factory:
            mock_factory.return_value.return_value = mock_cm
            # Must not raise
            await deduct_balance("user-123", Decimal("0.005"))


# ── credit_balance ────────────────────────────────────────────────────────────

class TestCreditBalance:

    async def test_credits_balance_for_new_user(self, mock_db):
        """INSERT ... ON CONFLICT is executed and session is not committed here
        (caller's session handles commit)."""
        from app.usage.balance import credit_balance

        await credit_balance("new-user", Decimal("10.00"), mock_db)

        mock_db.execute.assert_called_once()

    async def test_credits_balance_for_existing_user(self, mock_db):
        """Upsert executes regardless of whether row exists — DB handles conflict."""
        from app.usage.balance import credit_balance

        await credit_balance("existing-user", Decimal("5.50"), mock_db)

        mock_db.execute.assert_called_once()

    async def test_small_fractional_amount(self, mock_db):
        """Fractional cent amounts are handled correctly."""
        from app.usage.balance import credit_balance

        await credit_balance("user-123", Decimal("0.99"), mock_db)

        mock_db.execute.assert_called_once()
