"""
月謝リマインドエージェントのユニットテスト。
日付判定・メッセージ生成は純粋関数として検証し、
DB / LINE はモックで分離する。
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.payment_reminder import (
    build_reminder_message,
    determine_reminder_type,
    run_payment_reminders,
)
from app.models import Invoice


# ── リマインド種別判定 ────────────────────────────────────────────────────


class TestDetermineReminderType:
    def _invoice_date(self, due_offset: int) -> date:
        from datetime import timedelta
        return date.today() + timedelta(days=due_offset)

    def test_3日前(self):
        assert determine_reminder_type(self._invoice_date(3), date.today()) == "3days_before"

    def test_当日(self):
        assert determine_reminder_type(self._invoice_date(0), date.today()) == "due_day"

    def test_3日後(self):
        assert determine_reminder_type(self._invoice_date(-3), date.today()) == "3days_after"

    def test_2日前はNone(self):
        assert determine_reminder_type(self._invoice_date(2), date.today()) is None

    def test_1日前はNone(self):
        assert determine_reminder_type(self._invoice_date(1), date.today()) is None

    def test_1日後はNone(self):
        assert determine_reminder_type(self._invoice_date(-1), date.today()) is None

    def test_7日前はNone(self):
        assert determine_reminder_type(self._invoice_date(7), date.today()) is None

    def test_固定日付で3日前(self):
        due = date(2026, 6, 10)
        today = date(2026, 6, 7)
        assert determine_reminder_type(due, today) == "3days_before"

    def test_固定日付で当日(self):
        due = date(2026, 6, 10)
        today = date(2026, 6, 10)
        assert determine_reminder_type(due, today) == "due_day"

    def test_固定日付で3日後(self):
        due = date(2026, 6, 10)
        today = date(2026, 6, 13)
        assert determine_reminder_type(due, today) == "3days_after"


# ── メッセージ生成 ────────────────────────────────────────────────────────


def _make_invoice() -> Invoice:
    return Invoice(
        id="inv-001",
        student_id="stu-001",
        line_user_id="U_parent_001",
        amount=15000,
        due_date=date(2026, 6, 30),
        status="pending",
        month="2026-06",
    )


class TestBuildReminderMessage:
    def test_3日前メッセージに金額が含まれる(self):
        inv = _make_invoice()
        msg = build_reminder_message("3days_before", inv)
        assert "15,000円" in msg
        assert "2026-06" in msg

    def test_当日メッセージに期日が含まれる(self):
        inv = _make_invoice()
        msg = build_reminder_message("due_day", inv)
        assert "15,000円" in msg
        assert "本日" in msg

    def test_3日後メッセージに催促が含まれる(self):
        inv = _make_invoice()
        msg = build_reminder_message("3days_after", inv)
        assert "15,000円" in msg
        assert "確認できておりません" in msg

    def test_金額がカンマ区切り(self):
        inv = Invoice(
            id="inv-002",
            student_id="stu-002",
            line_user_id="U_parent_002",
            amount=20000,
            due_date=date(2026, 6, 30),
            status="pending",
            month="2026-06",
        )
        msg = build_reminder_message("due_day", inv)
        assert "20,000円" in msg


# ── run_payment_reminders（統合テスト・モック）───────────────────────────


@pytest.mark.asyncio
@patch("app.agents.payment_reminder.get_unpaid_invoices", new_callable=AsyncMock)
@patch("app.agents.payment_reminder.has_reminder_sent", new_callable=AsyncMock)
@patch("app.agents.payment_reminder.log_reminder", new_callable=AsyncMock)
@patch("app.agents.payment_reminder.push_text", new_callable=AsyncMock)
async def test_リマインド送信(mock_push, mock_log, mock_has, mock_invoices):
    """対象請求があり未送信なら push_text が呼ばれる"""
    mock_invoices.return_value = [
        Invoice(
            id="inv-001",
            student_id="stu-001",
            line_user_id="U_parent_001",
            amount=15000,
            due_date=date.today(),  # 当日 → due_day
            status="pending",
            month="2026-06",
        )
    ]
    mock_has.return_value = False

    count = await run_payment_reminders()

    assert count == 1
    mock_push.assert_called_once()
    mock_log.assert_called_once()


@pytest.mark.asyncio
@patch("app.agents.payment_reminder.get_unpaid_invoices", new_callable=AsyncMock)
@patch("app.agents.payment_reminder.has_reminder_sent", new_callable=AsyncMock)
@patch("app.agents.payment_reminder.push_text", new_callable=AsyncMock)
async def test_送信済みはスキップ(mock_push, mock_has, mock_invoices):
    """すでに送信済みの場合は重複送信しない"""
    mock_invoices.return_value = [
        Invoice(
            id="inv-001",
            student_id="stu-001",
            line_user_id="U_parent_001",
            amount=15000,
            due_date=date.today(),
            status="pending",
            month="2026-06",
        )
    ]
    mock_has.return_value = True  # 送信済み

    count = await run_payment_reminders()

    assert count == 0
    mock_push.assert_not_called()


@pytest.mark.asyncio
@patch("app.agents.payment_reminder.get_unpaid_invoices", new_callable=AsyncMock)
@patch("app.agents.payment_reminder.push_text", new_callable=AsyncMock)
async def test_対象外日付はスキップ(mock_push, mock_invoices):
    """リマインド対象外の日付は送信しない"""
    from datetime import timedelta
    mock_invoices.return_value = [
        Invoice(
            id="inv-001",
            student_id="stu-001",
            line_user_id="U_parent_001",
            amount=15000,
            due_date=date.today() + timedelta(days=5),  # 5日後 → 対象外
            status="pending",
            month="2026-06",
        )
    ]

    count = await run_payment_reminders()

    assert count == 0
    mock_push.assert_not_called()
