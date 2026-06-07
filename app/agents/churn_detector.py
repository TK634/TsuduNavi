"""
退塾リスク検知エージェント。

【スコアリング設計】
  出席率スコア  (max 40点): 直近4週間の出席率を評価
  成績スコア    (max 35点): 直近2テストの点数変化を評価
  連絡スコア    (max 25点): 保護者への最終連絡からの経過日数を評価

  合計 0〜100点。70点以上を high リスクとして塾長に通知。
"""

import os
from datetime import datetime
from typing import List, Optional

from app.database import (
    get_all_students,
    get_last_contact,
    get_recent_attendances,
    get_recent_grades,
    update_student_risk,
)
from app.line_client import push_text
from app.models import RiskResult

# リスク判定閾値
_HIGH_THRESHOLD = 70
_MEDIUM_THRESHOLD = 40

# 各スコアの最大値（合計100）
_MAX_ATTENDANCE = 40
_MAX_GRADE = 35
_MAX_CONTACT = 25


# ── 公開インターフェース ──────────────────────────────────────────────────


async def run_churn_detection() -> List[RiskResult]:
    """
    全生徒の退塾リスクを計算し、high リスクの場合は塾長へ LINE 通知する。
    cron から呼び出されることを想定。
    """
    students = await get_all_students()
    results: List[RiskResult] = []

    for student in students:
        if not student.id:
            continue

        result = await calculate_risk_score(student.id, student.name)

        # Supabase のリスクスコアを更新
        await update_student_risk(student.id, result.score, result.level)
        results.append(result)

        # high リスクのみ塾長に通知
        if result.level == "high":
            await _notify_director(result)

    return results


async def calculate_risk_score(
    student_id: str, student_name: Optional[str] = None
) -> RiskResult:
    """
    1生徒のリスクスコアを計算して返す。
    DBアクセスを分離しているため単体テストでモックしやすい。
    """
    attendance_score = await _calc_attendance_score(student_id)
    grade_score = await _calc_grade_score(student_id)
    contact_score = await _calc_contact_score(student_id)

    total = attendance_score + grade_score + contact_score
    level = (
        "high" if total >= _HIGH_THRESHOLD
        else "medium" if total >= _MEDIUM_THRESHOLD
        else "low"
    )

    return RiskResult(
        student_id=student_id,
        student_name=student_name,
        score=total,
        level=level,
        attendance_score=attendance_score,
        grade_score=grade_score,
        contact_score=contact_score,
    )


# ── スコア計算（純粋関数部分はテスト可能に分離）─────────────────────────


def attendance_rate_to_score(rate: float) -> float:
    """出席率 → スコア変換（max 40）"""
    if rate >= 0.80:
        return 0
    if rate >= 0.70:
        return 15
    if rate >= 0.60:
        return 25
    return _MAX_ATTENDANCE  # 60%未満


def grade_change_to_score(change: float) -> float:
    """前回比成績変化 → スコア変換（max 35）。下落が大きいほど高スコア"""
    if change >= 0:
        return 0      # 維持・向上
    if change >= -5:
        return 12     # 5点未満の下落
    if change >= -10:
        return 22     # 10点未満の下落
    return _MAX_GRADE  # 10点以上の下落


def days_to_score(days: int) -> float:
    """最終連絡からの経過日数 → スコア変換（max 25）"""
    if days <= 7:
        return 0
    if days <= 14:
        return 8
    if days <= 21:
        return 16
    return _MAX_CONTACT  # 21日超 or 記録なし


# ── DB からのデータ取得 ──────────────────────────────────────────────────


async def _calc_attendance_score(student_id: str) -> float:
    records = await get_recent_attendances(student_id, weeks=4)
    if not records:
        return 0  # 記録なしは判定不能→スコアなし

    rate = sum(1 for r in records if r["attended"]) / len(records)
    return attendance_rate_to_score(rate)


async def _calc_grade_score(student_id: str) -> float:
    grades = await get_recent_grades(student_id, limit=2)
    if len(grades) < 2:
        return 0  # 比較できる成績が足りない

    change = float(grades[0]["score"]) - float(grades[1]["score"])
    return grade_change_to_score(change)


async def _calc_contact_score(student_id: str) -> float:
    last = await get_last_contact(student_id)
    if last is None:
        return _MAX_CONTACT  # 連絡記録なし→最大スコア

    days = (datetime.now() - last).days
    return days_to_score(days)


# ── 塾長への通知 ─────────────────────────────────────────────────────────


async def _notify_director(result: RiskResult) -> None:
    """塾長の LINE にリスク検知通知を送る"""
    director_id = os.environ.get("DIRECTOR_LINE_USER_ID", "")
    if not director_id:
        return

    message = (
        f"⚠️ 退塾リスク検知\n\n"
        f"生徒: {result.student_name or '（名前未設定）'}\n"
        f"リスクスコア: {result.score:.0f} / 100点\n\n"
        f"【内訳】\n"
        f"  出席: {result.attendance_score:.0f}点\n"
        f"  成績: {result.grade_score:.0f}点\n"
        f"  連絡: {result.contact_score:.0f}点\n\n"
        f"早急なフォローをお勧めします。"
    )
    await push_text(director_id, message)
