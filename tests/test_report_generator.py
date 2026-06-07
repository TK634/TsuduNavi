"""
授業報告自動生成エージェントのユニットテスト。
メッセージパースは純粋関数として検証し、
DB / LINE / Claude API はモックで分離する。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.report_generator import (
    parse_report_message,
    process_teacher_message,
)
from app.models import LessonReport


# ── メッセージパース ──────────────────────────────────────────────────────


class TestParseReportMessage:
    def test_正常形式(self):
        msg = "報告 山田太郎\n今日は方程式の演習をしました。"
        name, memo = parse_report_message(msg)
        assert name == "山田太郎"
        assert "方程式" in memo

    def test_生徒名に空白あり(self):
        name, memo = parse_report_message("報告 田中 花子\nメモ内容")
        assert name == "田中 花子"
        assert memo == "メモ内容"

    def test_報告キーワードなしはNone(self):
        name, memo = parse_report_message("山田太郎\n授業内容")
        assert name is None
        assert memo is None

    def test_生徒名が空はNone(self):
        name, memo = parse_report_message("報告\nメモ")
        assert name is None
        assert memo is None

    def test_メモが空はNone(self):
        name, memo = parse_report_message("報告 山田太郎")
        assert name == "山田太郎"
        assert memo is None

    def test_メモが改行後に空白のみはNone(self):
        name, memo = parse_report_message("報告 山田太郎\n   ")
        assert name == "山田太郎"
        assert memo is None

    def test_複数行のメモ(self):
        msg = "報告 山田太郎\n1行目\n2行目\n3行目"
        name, memo = parse_report_message(msg)
        assert name == "山田太郎"
        assert "1行目" in memo
        assert "2行目" in memo


# ── process_teacher_message（DBモック）───────────────────────────────────


@pytest.mark.asyncio
@patch("app.agents.report_generator.get_pending_report", new_callable=AsyncMock)
@patch("app.agents.report_generator.get_student_by_name", new_callable=AsyncMock)
@patch("app.agents.report_generator.create_lesson_report", new_callable=AsyncMock)
@patch("app.agents.report_generator._generate_report_text", new_callable=AsyncMock)
async def test_新規報告の作成(mock_gen, mock_create, mock_student, mock_pending):
    """正しい形式のメッセージで下書きが作成される"""
    mock_pending.return_value = None
    mock_student.return_value = MagicMock(
        id="stu-001", line_user_id="U_parent_001"
    )
    mock_gen.return_value = "本日は方程式の演習を行いました。山田さんは積極的に取り組んでいました。"
    mock_create.return_value = MagicMock(id="rep-001")

    result = await process_teacher_message(
        "U_teacher_001",
        "報告 山田太郎\n方程式の演習。符号ミスが多い。",
    )

    assert "下書き" in result
    assert "送信" in result
    mock_gen.assert_called_once()
    mock_create.assert_called_once()


@pytest.mark.asyncio
@patch("app.agents.report_generator.get_pending_report", new_callable=AsyncMock)
async def test_不正形式のメッセージ(mock_pending):
    """形式が不正なメッセージはガイダンスを返す"""
    mock_pending.return_value = None

    result = await process_teacher_message("U_teacher_001", "こんにちは")

    assert "形式" in result
    assert "報告" in result


@pytest.mark.asyncio
@patch("app.agents.report_generator.get_pending_report", new_callable=AsyncMock)
@patch("app.agents.report_generator.push_text", new_callable=AsyncMock)
@patch("app.agents.report_generator.update_report_status", new_callable=AsyncMock)
async def test_送信確認(mock_update, mock_push, mock_pending):
    """「送信」と返信すると保護者に送信される"""
    mock_pending.return_value = LessonReport(
        id="rep-001",
        teacher_line_user_id="U_teacher_001",
        raw_content="生メモ",
        generated_content="丁寧な連絡帳文章",
        parent_line_user_id="U_parent_001",
    )

    result = await process_teacher_message("U_teacher_001", "送信")

    assert "送信しました" in result
    mock_push.assert_called_once_with("U_parent_001", "丁寧な連絡帳文章")
    mock_update.assert_called_once_with("rep-001", "sent")


@pytest.mark.asyncio
@patch("app.agents.report_generator.get_pending_report", new_callable=AsyncMock)
@patch("app.agents.report_generator.update_report_status", new_callable=AsyncMock)
async def test_キャンセル(mock_update, mock_pending):
    """「キャンセル」と返信すると下書きが破棄される"""
    mock_pending.return_value = LessonReport(
        id="rep-001",
        teacher_line_user_id="U_teacher_001",
        raw_content="生メモ",
        generated_content="丁寧な文章",
    )

    result = await process_teacher_message("U_teacher_001", "キャンセル")

    assert "キャンセル" in result
    mock_update.assert_called_once_with("rep-001", "cancelled")


@pytest.mark.asyncio
@patch("app.agents.report_generator.get_pending_report", new_callable=AsyncMock)
async def test_ペンディング中に別メッセージ(mock_pending):
    """確認待ち中に別のメッセージを送ると現在の下書きを再提示する"""
    mock_pending.return_value = LessonReport(
        id="rep-001",
        teacher_line_user_id="U_teacher_001",
        raw_content="生メモ",
        generated_content="丁寧な文章",
    )

    result = await process_teacher_message("U_teacher_001", "あ、間違えました")

    assert "送信待ち" in result
