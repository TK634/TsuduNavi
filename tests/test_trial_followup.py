"""
体験授業後フォローアップエージェントのユニットテスト。
フォローアップ送信ロジックをモックで分離して検証する。
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.trial_followup import run_trial_followups
from app.models import Booking


def _make_booking(completed_days_ago: int, booking_id: str = "book-001") -> Booking:
    """指定日数前に体験完了したダミー予約を作成するヘルパー"""
    completed_at = datetime.now() - timedelta(days=completed_days_ago)
    return Booking(
        id=booking_id,
        line_user_id="U_parent_001",
        student_name="山田太郎",
        grade="中3",
        subject="数学",
        scheduled_at=completed_at - timedelta(hours=1),
        trial_completed_at=completed_at,
        trial_notes="二次方程式の体験。理解度は高め。",
    )


# ── 送信タイミング ────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.agents.trial_followup.get_completed_trials_for_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.has_followup_sent", new_callable=AsyncMock)
@patch("app.agents.trial_followup.log_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.generate_followup_message", new_callable=AsyncMock)
@patch("app.agents.trial_followup.push_text", new_callable=AsyncMock)
async def test_3日後フォローアップを送信(mock_push, mock_gen, mock_log, mock_has, mock_trials):
    """体験完了から3日後に 3day フォローアップを送信する"""
    mock_trials.return_value = [_make_booking(completed_days_ago=3)]
    mock_has.return_value = False
    mock_gen.return_value = "体験はいかがでしたか？"

    count = await run_trial_followups()

    assert count == 1
    mock_gen.assert_called_once()
    mock_push.assert_called_once_with("U_parent_001", "体験はいかがでしたか？")
    mock_log.assert_called_once_with("book-001", "3day")


@pytest.mark.asyncio
@patch("app.agents.trial_followup.get_completed_trials_for_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.has_followup_sent", new_callable=AsyncMock)
@patch("app.agents.trial_followup.log_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.generate_followup_message", new_callable=AsyncMock)
@patch("app.agents.trial_followup.push_text", new_callable=AsyncMock)
async def test_7日後に両方送信(mock_push, mock_gen, mock_log, mock_has, mock_trials):
    """体験完了から7日後には 3day と 1week の両方を送信する"""
    mock_trials.return_value = [_make_booking(completed_days_ago=7)]
    mock_has.return_value = False  # どちらも未送信
    mock_gen.return_value = "フォローアップメッセージ"

    count = await run_trial_followups()

    assert count == 2
    assert mock_push.call_count == 2


@pytest.mark.asyncio
@patch("app.agents.trial_followup.get_completed_trials_for_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.has_followup_sent", new_callable=AsyncMock)
@patch("app.agents.trial_followup.push_text", new_callable=AsyncMock)
async def test_2日後はまだ送信しない(mock_push, mock_has, mock_trials):
    """体験完了から2日後はまだ 3day フォローアップを送らない"""
    mock_trials.return_value = [_make_booking(completed_days_ago=2)]
    mock_has.return_value = False

    count = await run_trial_followups()

    assert count == 0
    mock_push.assert_not_called()


@pytest.mark.asyncio
@patch("app.agents.trial_followup.get_completed_trials_for_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.has_followup_sent", new_callable=AsyncMock)
@patch("app.agents.trial_followup.push_text", new_callable=AsyncMock)
async def test_送信済みはスキップ(mock_push, mock_has, mock_trials):
    """3day も 1week もすでに送信済みの場合は何も送らない"""
    mock_trials.return_value = [_make_booking(completed_days_ago=10)]
    mock_has.return_value = True  # すべて送信済み

    count = await run_trial_followups()

    assert count == 0
    mock_push.assert_not_called()


@pytest.mark.asyncio
@patch("app.agents.trial_followup.get_completed_trials_for_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.has_followup_sent", new_callable=AsyncMock)
@patch("app.agents.trial_followup.log_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.generate_followup_message", new_callable=AsyncMock)
@patch("app.agents.trial_followup.push_text", new_callable=AsyncMock)
async def test_3day送信済みで1weekのみ送信(mock_push, mock_gen, mock_log, mock_has, mock_trials):
    """3day 送信済みの場合は 1week だけ送信する"""
    mock_trials.return_value = [_make_booking(completed_days_ago=8)]
    mock_gen.return_value = "1週間後のメッセージ"

    # 3day 済み、1week 未送信
    async def has_sent_side_effect(booking_id, followup_type):
        return followup_type == "3day"

    mock_has.side_effect = has_sent_side_effect

    count = await run_trial_followups()

    assert count == 1
    mock_log.assert_called_once_with("book-001", "1week")


@pytest.mark.asyncio
@patch("app.agents.trial_followup.get_completed_trials_for_followup", new_callable=AsyncMock)
@patch("app.agents.trial_followup.push_text", new_callable=AsyncMock)
async def test_trial_completed_atなしはスキップ(mock_push, mock_trials):
    """trial_completed_at が None の予約はスキップする"""
    booking = Booking(
        id="book-002",
        line_user_id="U_parent_002",
        student_name="田中花子",
        grade="小5",
        subject="算数",
        scheduled_at=datetime.now() - timedelta(days=10),
        trial_completed_at=None,  # 未完了
    )
    mock_trials.return_value = [booking]

    count = await run_trial_followups()

    assert count == 0
    mock_push.assert_not_called()
