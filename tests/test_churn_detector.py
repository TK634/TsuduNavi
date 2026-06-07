"""
退塾リスク検知エージェントのユニットテスト。
スコアリング純粋関数はモックなしで検証し、
DB アクセスを含む関数はモックで分離する。
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.churn_detector import (
    _HIGH_THRESHOLD,
    _MEDIUM_THRESHOLD,
    _MAX_ATTENDANCE,
    _MAX_CONTACT,
    _MAX_GRADE,
    attendance_rate_to_score,
    calculate_risk_score,
    days_to_score,
    grade_change_to_score,
)
from app.models import RiskResult


# ── 出席率スコア変換 ──────────────────────────────────────────────────────


class TestAttendanceRateToScore:
    def test_全出席はゼロ点(self):
        assert attendance_rate_to_score(1.0) == 0

    def test_80パーセントはゼロ点(self):
        assert attendance_rate_to_score(0.80) == 0

    def test_79パーセントは15点(self):
        assert attendance_rate_to_score(0.79) == 15

    def test_70パーセントは15点(self):
        assert attendance_rate_to_score(0.70) == 15

    def test_69パーセントは25点(self):
        assert attendance_rate_to_score(0.69) == 25

    def test_60パーセントは25点(self):
        assert attendance_rate_to_score(0.60) == 25

    def test_59パーセントは最大点(self):
        assert attendance_rate_to_score(0.59) == _MAX_ATTENDANCE

    def test_ゼロ出席は最大点(self):
        assert attendance_rate_to_score(0.0) == _MAX_ATTENDANCE


# ── 成績スコア変換 ────────────────────────────────────────────────────────


class TestGradeChangeToScore:
    def test_成績維持はゼロ点(self):
        assert grade_change_to_score(0) == 0

    def test_成績上昇はゼロ点(self):
        assert grade_change_to_score(10) == 0

    def test_4点下落は12点(self):
        assert grade_change_to_score(-4) == 12

    def test_5点下落は12点(self):
        assert grade_change_to_score(-5) == 12

    def test_6点下落は22点(self):
        assert grade_change_to_score(-6) == 22

    def test_10点下落は22点(self):
        assert grade_change_to_score(-10) == 22

    def test_11点下落は最大点(self):
        assert grade_change_to_score(-11) == _MAX_GRADE

    def test_大幅下落は最大点(self):
        assert grade_change_to_score(-50) == _MAX_GRADE


# ── 連絡スコア変換 ────────────────────────────────────────────────────────


class TestDaysToScore:
    def test_当日連絡はゼロ点(self):
        assert days_to_score(0) == 0

    def test_7日以内はゼロ点(self):
        assert days_to_score(7) == 0

    def test_8日は8点(self):
        assert days_to_score(8) == 8

    def test_14日は8点(self):
        assert days_to_score(14) == 8

    def test_15日は16点(self):
        assert days_to_score(15) == 16

    def test_21日は16点(self):
        assert days_to_score(21) == 16

    def test_22日は最大点(self):
        assert days_to_score(22) == _MAX_CONTACT

    def test_30日超は最大点(self):
        assert days_to_score(100) == _MAX_CONTACT


# ── リスクレベル判定 ──────────────────────────────────────────────────────


class TestRiskLevel:
    def _make_result(self, score: float) -> RiskResult:
        level = (
            "high" if score >= _HIGH_THRESHOLD
            else "medium" if score >= _MEDIUM_THRESHOLD
            else "low"
        )
        return RiskResult(
            student_id="test",
            student_name="テスト生徒",
            score=score,
            level=level,
            attendance_score=0,
            grade_score=0,
            contact_score=0,
        )

    def test_スコア0はlow(self):
        assert self._make_result(0).level == "low"

    def test_スコア39はlow(self):
        assert self._make_result(39).level == "low"

    def test_スコア40はmedium(self):
        assert self._make_result(40).level == "medium"

    def test_スコア69はmedium(self):
        assert self._make_result(69).level == "medium"

    def test_スコア70はhigh(self):
        assert self._make_result(70).level == "high"

    def test_スコア100はhigh(self):
        assert self._make_result(100).level == "high"


# ── calculate_risk_score（DBモック）──────────────────────────────────────


@pytest.mark.asyncio
@patch("app.agents.churn_detector.get_recent_attendances", new_callable=AsyncMock)
@patch("app.agents.churn_detector.get_recent_grades", new_callable=AsyncMock)
@patch("app.agents.churn_detector.get_last_contact", new_callable=AsyncMock)
async def test_高リスク生徒(mock_contact, mock_grades, mock_attendance):
    """出席率低下 + 成績下落 + 連絡なし → high リスク"""
    # 出席4回中1回のみ出席（出席率25% → 40点）
    mock_attendance.return_value = [
        {"attended": True},
        {"attended": False},
        {"attended": False},
        {"attended": False},
    ]
    # 成績が80 → 60（-20点 → 35点）
    mock_grades.return_value = [
        {"score": 60, "test_date": "2026-06-01"},
        {"score": 80, "test_date": "2026-05-01"},
    ]
    # 最終連絡なし（25点）
    mock_contact.return_value = None

    result = await calculate_risk_score("student-001", "テスト生徒")

    assert result.level == "high"
    assert result.score == 40 + 35 + 25  # 100点


@pytest.mark.asyncio
@patch("app.agents.churn_detector.get_recent_attendances", new_callable=AsyncMock)
@patch("app.agents.churn_detector.get_recent_grades", new_callable=AsyncMock)
@patch("app.agents.churn_detector.get_last_contact", new_callable=AsyncMock)
async def test_低リスク生徒(mock_contact, mock_grades, mock_attendance):
    """全出席 + 成績向上 + 最近連絡あり → low リスク"""
    mock_attendance.return_value = [
        {"attended": True},
        {"attended": True},
        {"attended": True},
        {"attended": True},
    ]
    mock_grades.return_value = [
        {"score": 85, "test_date": "2026-06-01"},
        {"score": 80, "test_date": "2026-05-01"},
    ]
    from datetime import datetime
    mock_contact.return_value = datetime.now()

    result = await calculate_risk_score("student-002", "優秀生徒")

    assert result.level == "low"
    assert result.score == 0
