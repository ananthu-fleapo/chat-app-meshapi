"""
Tests for deduct_balance and credit_balance ledger integration.

Coverage:
- deduct_balance writes a BalanceLedger row with correct fields
- deduct_balance handles missing balance row (balance_before=0)
- deduct_balance with usage_event_id=None leaves reference_id=None
- deduct_balance skips on zero cost (no DB calls)
- deduct_balance swallows DB errors (fire-and-forget preserved)
- credit_balance writes a BalanceLedger row with correct fields
- credit_balance does NOT call db.commit()
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# conftest sets env vars before any app imports


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_balance_row(balance_usd: Decimal) -> MagicMock:
    row = MagicMock()
    row.balance_usd = balance_usd
    return row


def _make_session(*, balance_row=None):
    """Build a mock session whose SELECT FOR UPDATE returns balance_row."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = balance_row

    # execute() is called twice in deduct_balance: SELECT FOR UPDATE, then INSERT upsert
    session.execute = AsyncMock(return_value=select_result)
    return session


def _make_session_cm(session):
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = False
    return cm


# ── deduct_balance ────────────────────────────────────────────────────────────

class TestDeductBalance:
    @pytest.mark.asyncio
    async def test_writes_ledger_row_with_correct_fields(self):
        from app.usage.balance import deduct_balance
        from app.db.models import BalanceLedger

        owner = "user-abc"
        cost = Decimal("0.001234")
        current = Decimal("5.000000")
        event_id = uuid.uuid4()

        session = _make_session(balance_row=_make_balance_row(current))

        with patch(
            "app.usage.balance.get_session_factory",
            return_value=lambda: _make_session_cm(session),
        ):
            await deduct_balance(owner, cost, usage_event_id=event_id)

        session.add.assert_called_once()
        ledger: BalanceLedger = session.add.call_args[0][0]
        assert isinstance(ledger, BalanceLedger)
        assert ledger.user_id == owner
        assert ledger.txn_type == "debit"
        assert ledger.amount_usd == cost
        assert ledger.balance_before == current
        assert ledger.balance_after == current - cost
        assert ledger.reference_id == event_id
        assert ledger.reference_type == "usage_event"

    @pytest.mark.asyncio
    async def test_missing_balance_row_uses_zero_before(self):
        from app.usage.balance import deduct_balance
        from app.db.models import BalanceLedger

        session = _make_session(balance_row=None)

        with patch(
            "app.usage.balance.get_session_factory",
            return_value=lambda: _make_session_cm(session),
        ):
            await deduct_balance("user-new", Decimal("0.0005"))

        ledger: BalanceLedger = session.add.call_args[0][0]
        assert ledger.balance_before == Decimal("0")
        assert ledger.balance_after == Decimal("-0.0005")

    @pytest.mark.asyncio
    async def test_null_usage_event_id_leaves_reference_none(self):
        from app.usage.balance import deduct_balance
        from app.db.models import BalanceLedger

        session = _make_session(balance_row=_make_balance_row(Decimal("2.0")))

        with patch(
            "app.usage.balance.get_session_factory",
            return_value=lambda: _make_session_cm(session),
        ):
            await deduct_balance("owner", Decimal("0.01"), usage_event_id=None)

        ledger: BalanceLedger = session.add.call_args[0][0]
        assert ledger.reference_id is None
        assert ledger.reference_type is None

    @pytest.mark.asyncio
    async def test_zero_cost_skips_all_db_calls(self):
        from app.usage.balance import deduct_balance

        factory = MagicMock()
        with patch("app.usage.balance.get_session_factory", factory):
            await deduct_balance("owner", Decimal("0"))

        factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_db_error_is_swallowed(self):
        from app.usage.balance import deduct_balance

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=RuntimeError("db dead"))
        cm = AsyncMock()
        cm.__aenter__.return_value = session
        cm.__aexit__.return_value = False

        with patch(
            "app.usage.balance.get_session_factory",
            return_value=lambda: cm,
        ):
            # Must not raise
            await deduct_balance("owner", Decimal("1.0"))


# ── credit_balance ────────────────────────────────────────────────────────────

class TestCreditBalance:
    @pytest.mark.asyncio
    async def test_writes_ledger_row_with_correct_fields(self):
        from app.usage.balance import credit_balance
        from app.db.models import BalanceLedger

        user_id = "user-xyz"
        amount = Decimal("10.000000")
        current = Decimal("3.500000")
        payment_id = uuid.uuid4()

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = _make_balance_row(current)
        db.execute = AsyncMock(return_value=select_result)

        await credit_balance(user_id, amount, db, payment_event_id=payment_id)

        db.add.assert_called_once()
        ledger: BalanceLedger = db.add.call_args[0][0]
        assert isinstance(ledger, BalanceLedger)
        assert ledger.user_id == user_id
        assert ledger.txn_type == "credit"
        assert ledger.amount_usd == amount
        assert ledger.balance_before == current
        assert ledger.balance_after == current + amount
        assert ledger.reference_id == payment_id
        assert ledger.reference_type == "payment_event"

    @pytest.mark.asyncio
    async def test_new_user_uses_zero_balance_before(self):
        from app.usage.balance import credit_balance
        from app.db.models import BalanceLedger

        db = AsyncMock()
        db.add = MagicMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None  # no existing row
        db.execute = AsyncMock(return_value=select_result)

        await credit_balance("new-user", Decimal("5.0"), db)

        ledger: BalanceLedger = db.add.call_args[0][0]
        assert ledger.balance_before == Decimal("0")
        assert ledger.balance_after == Decimal("5.0")

    @pytest.mark.asyncio
    async def test_null_payment_event_id_leaves_reference_none(self):
        from app.usage.balance import credit_balance
        from app.db.models import BalanceLedger

        db = AsyncMock()
        db.add = MagicMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=select_result)

        await credit_balance("user", Decimal("1.0"), db, payment_event_id=None)

        ledger: BalanceLedger = db.add.call_args[0][0]
        assert ledger.reference_id is None
        assert ledger.reference_type is None

    @pytest.mark.asyncio
    async def test_does_not_commit(self):
        from app.usage.balance import credit_balance

        db = AsyncMock()
        db.add = MagicMock()

        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=select_result)

        await credit_balance("user", Decimal("2.0"), db)

        db.commit.assert_not_called()
