"""
Unit tests for app/usage/balance.py

Covers:
  check_balance       — free model bypass, paid model pass/block, unknown model
  deduct_balance      — happy path, zero cost skip, DB error swallowed
  credit_balance      — new user insert, existing user increment
  get_active_discount — model-level, account-level, priority, expiry warning,
                        future valid_from, no-expiry (valid_until=None)
"""

from decimal import Decimal
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_execute_result


def _make_model_price(is_free: bool = False) -> MagicMock:
    """Build a ModelPrice-like mock."""
    mp = MagicMock()
    mp.is_free = is_free
    mp.prompt_usd_per_1k = Decimal("0.003000")
    mp.completion_usd_per_1k = Decimal("0.015000")
    return mp


def _make_discount(
    discount_pct: Decimal = Decimal("10.00"),
    valid_from_offset_days: int = -10,   # negative = past, positive = future
    valid_until_offset_days: int | None = None,  # None = no expiry
    model_id: str | None = "openai/gpt-4o",
) -> MagicMock:
    """Build a Discount-like mock with real datetime objects."""
    d = MagicMock()
    d.id = "discount-test-id"
    d.discount_pct = discount_pct
    d.model_id = model_id
    d.valid_from = datetime.now(UTC) + timedelta(days=valid_from_offset_days)
    if valid_until_offset_days is None:
        d.valid_until = None
    else:
        d.valid_until = datetime.now(UTC) + timedelta(days=valid_until_offset_days)
    return d


# ── check_balance ─────────────────────────────────────────────────────────────

class TestCheckBalance:

    async def test_free_model_skips_balance_check(self, mock_db):
        """Free model always passes regardless of balance."""
        from app.usage.balance import check_balance

        # model_prices row: is_free = True
        mock_db.execute.return_value = make_execute_result(scalar=_make_model_price(is_free=True))

        # Should not raise even though we never query user_balances
        await check_balance("user-123", "meta-llama/llama-3-free", mock_db)

        # Only one execute call — balance was never queried
        assert mock_db.execute.call_count == 1

    async def test_paid_model_with_positive_balance_passes(self, mock_db):
        """Paid model with balance > 0 proceeds."""
        from app.usage.balance import check_balance

        # First call: model_prices → paid model
        # Second call: user_balances → balance = 5.00
        mock_db.execute.side_effect = [
            make_execute_result(scalar=_make_model_price(is_free=False)),
            make_execute_result(rows=[(Decimal("5.000000"),)]),
        ]

        await check_balance("user-123", "openai/gpt-4o", mock_db)  # no exception

    async def test_paid_model_with_zero_balance_raises_402(self, mock_db):
        """Paid model with balance = 0 → PaymentRequiredError."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(scalar=_make_model_price(is_free=False)),
            make_execute_result(rows=[(Decimal("0"),)]),
        ]

        with pytest.raises(PaymentRequiredError):
            await check_balance("user-123", "openai/gpt-4o", mock_db)

    async def test_paid_model_with_negative_balance_raises_402(self, mock_db):
        """Balance that went slightly negative (post-deduction overshoot) still blocks."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(scalar=_make_model_price(is_free=False)),
            make_execute_result(rows=[(Decimal("-0.000500"),)]),
        ]

        with pytest.raises(PaymentRequiredError):
            await check_balance("user-123", "openai/gpt-4o", mock_db)

    async def test_unknown_model_is_allowed(self, mock_db):
        """Model not in model_prices is allowed through — admin hasn't priced it yet."""
        from app.usage.balance import check_balance

        mock_db.execute.return_value = make_execute_result(scalar=None)  # not in table

        # Should not raise even with zero balance — only one execute call (price lookup)
        await check_balance("user-123", "unknown/model-x", mock_db)
        assert mock_db.execute.call_count == 1

    async def test_no_balance_row_treated_as_zero(self, mock_db):
        """User with no balance row → treated as $0 → blocked for explicitly paid model."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(scalar=_make_model_price(is_free=False)),
            make_execute_result(rows=None),  # no balance row → zero
        ]

        with pytest.raises(PaymentRequiredError):
            await check_balance("new-user", "openai/gpt-4o", mock_db)

    async def test_error_message_mentions_top_up(self, mock_db):
        """402 error message should guide the user."""
        from app.usage.balance import check_balance
        from app.exceptions import PaymentRequiredError

        mock_db.execute.side_effect = [
            make_execute_result(scalar=_make_model_price(is_free=False)),
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


# ── get_active_discount ───────────────────────────────────────────────────────

class TestGetActiveDiscount:

    async def test_no_discount_returns_none(self, mock_db):
        """No discount row for model or account → returns None."""
        from app.usage.balance import get_active_discount

        mock_db.execute.return_value = make_execute_result(scalar=None)
        result = await get_active_discount("owner", "openai/gpt-4o", mock_db)
        assert result is None

    async def test_active_model_level_discount_returned(self, mock_db):
        """Active model-level discount → returns its discount_pct."""
        from app.usage.balance import get_active_discount

        discount = _make_discount(discount_pct=Decimal("20.00"), model_id="openai/gpt-4o")
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        result = await get_active_discount("owner", "openai/gpt-4o", mock_db)
        assert result == Decimal("20.00")

    async def test_account_level_discount_used_when_no_model_level(self, mock_db):
        """Model-level miss → falls through to account-level discount."""
        from app.usage.balance import get_active_discount

        account_discount = _make_discount(discount_pct=Decimal("5.00"), model_id=None)
        mock_db.execute.side_effect = [
            make_execute_result(scalar=None),            # model-level: miss
            make_execute_result(scalar=account_discount),  # account-level: hit
        ]

        result = await get_active_discount("owner", "openai/gpt-4o", mock_db)
        assert result == Decimal("5.00")

    async def test_model_level_takes_priority_over_account_level(self, mock_db):
        """Model-level hit → account-level is never queried."""
        from app.usage.balance import get_active_discount

        model_discount = _make_discount(discount_pct=Decimal("30.00"), model_id="openai/gpt-4o")
        mock_db.execute.return_value = make_execute_result(scalar=model_discount)

        result = await get_active_discount("owner", "openai/gpt-4o", mock_db)
        assert result == Decimal("30.00")
        # Only one DB call — stopped at model-level hit
        assert mock_db.execute.call_count == 1

    async def test_expired_discount_logs_warning_and_returns_none(self, mock_db):
        """Expired discount (valid_until < now) → warning logged, returns None."""
        from app.usage.balance import get_active_discount

        expired = _make_discount(
            discount_pct=Decimal("15.00"),
            valid_from_offset_days=-30,
            valid_until_offset_days=-1,   # expired yesterday
        )
        mock_db.execute.side_effect = [
            make_execute_result(scalar=expired),  # model-level: expired
            make_execute_result(scalar=None),     # account-level: no discount
        ]

        with patch("app.usage.balance.logger") as mock_logger:
            result = await get_active_discount("owner", "openai/gpt-4o", mock_db)

        assert result is None
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert warning_call == "discount_expired"

    async def test_expired_model_level_falls_through_to_account_level(self, mock_db):
        """Expired model-level discount → skips to account-level (which is active)."""
        from app.usage.balance import get_active_discount

        expired_model = _make_discount(
            discount_pct=Decimal("25.00"),
            valid_until_offset_days=-1,  # expired
            model_id="openai/gpt-4o",
        )
        active_account = _make_discount(
            discount_pct=Decimal("10.00"),
            valid_until_offset_days=None,  # no expiry
            model_id=None,
        )
        mock_db.execute.side_effect = [
            make_execute_result(scalar=expired_model),
            make_execute_result(scalar=active_account),
        ]

        with patch("app.usage.balance.logger"):
            result = await get_active_discount("owner", "openai/gpt-4o", mock_db)

        assert result == Decimal("10.00")

    async def test_future_valid_from_skipped_silently(self, mock_db):
        """Discount whose valid_from is in the future → skipped, no warning."""
        from app.usage.balance import get_active_discount

        future_discount = _make_discount(
            discount_pct=Decimal("10.00"),
            valid_from_offset_days=+5,  # starts 5 days from now
        )
        mock_db.execute.return_value = make_execute_result(scalar=future_discount)

        with patch("app.usage.balance.logger") as mock_logger:
            result = await get_active_discount("owner", "openai/gpt-4o", mock_db)

        assert result is None
        mock_logger.warning.assert_not_called()

    async def test_no_expiry_valid_until_none_is_active(self, mock_db):
        """Discount with valid_until=None (permanent) → treated as active."""
        from app.usage.balance import get_active_discount

        permanent = _make_discount(
            discount_pct=Decimal("50.00"),
            valid_until_offset_days=None,  # no expiry
        )
        mock_db.execute.return_value = make_execute_result(scalar=permanent)

        result = await get_active_discount("owner", "openai/gpt-4o", mock_db)
        assert result == Decimal("50.00")
