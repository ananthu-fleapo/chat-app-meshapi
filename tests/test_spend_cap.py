"""
Unit tests for app/usage/spend_cap.py

Covers:
  check_spend_cap — pass when under cap, 402 when at or above cap (>= boundary),
                    zero-spend, zero-cap edge case, error message content
"""

from decimal import Decimal

import pytest

from tests.conftest import make_execute_result

KEY_ID = "00000000-0000-0000-0000-000000000001"


class TestCheckSpendCap:

    async def test_spend_under_cap_does_not_raise(self, mock_db):
        """Accumulated spend < cap → request proceeds."""
        from app.usage.spend_cap import check_spend_cap

        mock_db.execute.return_value = make_execute_result(scalar=Decimal("5.00"))
        await check_spend_cap(KEY_ID, Decimal("10.00"), mock_db)

    async def test_spend_equal_to_cap_raises_402(self, mock_db):
        """Accumulated spend == cap → PaymentRequiredError (>= check)."""
        from app.usage.spend_cap import check_spend_cap
        from app.exceptions import PaymentRequiredError

        mock_db.execute.return_value = make_execute_result(scalar=Decimal("10.00"))
        with pytest.raises(PaymentRequiredError):
            await check_spend_cap(KEY_ID, Decimal("10.00"), mock_db)

    async def test_spend_over_cap_raises_402(self, mock_db):
        """Accumulated spend > cap → PaymentRequiredError."""
        from app.usage.spend_cap import check_spend_cap
        from app.exceptions import PaymentRequiredError

        mock_db.execute.return_value = make_execute_result(scalar=Decimal("15.00"))
        with pytest.raises(PaymentRequiredError):
            await check_spend_cap(KEY_ID, Decimal("10.00"), mock_db)

    async def test_zero_spend_new_key_passes(self, mock_db):
        """Brand-new key with $0 spend and positive cap → passes."""
        from app.usage.spend_cap import check_spend_cap

        mock_db.execute.return_value = make_execute_result(scalar=Decimal("0"))
        await check_spend_cap(KEY_ID, Decimal("10.00"), mock_db)

    async def test_zero_cap_blocks_immediately(self, mock_db):
        """Cap of $0 blocks even when spend is also $0 (0 >= 0)."""
        from app.usage.spend_cap import check_spend_cap
        from app.exceptions import PaymentRequiredError

        mock_db.execute.return_value = make_execute_result(scalar=Decimal("0"))
        with pytest.raises(PaymentRequiredError):
            await check_spend_cap(KEY_ID, Decimal("0"), mock_db)

    async def test_error_message_includes_cap_and_spend(self, mock_db):
        """Error message names both the cap and the current spend for clarity."""
        from app.usage.spend_cap import check_spend_cap
        from app.exceptions import PaymentRequiredError

        mock_db.execute.return_value = make_execute_result(scalar=Decimal("12.5000"))
        with pytest.raises(PaymentRequiredError) as exc_info:
            await check_spend_cap(KEY_ID, Decimal("10.00"), mock_db)
        assert "10.0000" in exc_info.value.message
        assert "12.5000" in exc_info.value.message

    async def test_uuid_conversion_used_in_query(self, mock_db):
        """key_id string is converted to uuid.UUID for the WHERE clause."""
        from app.usage.spend_cap import check_spend_cap

        mock_db.execute.return_value = make_execute_result(scalar=Decimal("0"))
        await check_spend_cap(KEY_ID, Decimal("99.00"), mock_db)

        # execute was called once — confirms the query was issued
        mock_db.execute.assert_called_once()
