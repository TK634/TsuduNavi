"""
体験授業後フォローアップエージェント。

【フォローアップスケジュール】
  3日後 : 体験の感想を聞く初回フォロー
  1週間後: 入塾検討状況を確認する2回目フォロー

Claude API で体験時のメモ（trial_notes）を参照し、
生徒の状況に合わせたパーソナライズドメッセージを生成する。
"""

import os
from datetime import datetime
from typing import List

import anthropic

from app.database import (
    get_completed_trials_for_followup,
    has_followup_sent,
    log_followup,
)
from app.line_client import push_text
from app.models import Booking

_claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


# ── 公開インターフェース ──────────────────────────────────────────────────


async def run_trial_followups() -> int:
    """
    体験授業完了後のフォローアップメッセージを送信する。
    戻り値: 実際に送信した件数。
    """
    bookings = await get_completed_trials_for_followup()
    sent_count = 0
    now = datetime.now()

    for booking in bookings:
        if not booking.trial_completed_at:
            continue

        days_elapsed = (now - booking.trial_completed_at).days

        # 3日後フォローアップ
        if days_elapsed >= 3 and not await has_followup_sent(booking.id, "3day"):
            message = await generate_followup_message(booking, "3day")
            await push_text(booking.line_user_id, message)
            await log_followup(booking.id, "3day")
            sent_count += 1

        # 1週間後フォローアップ
        if days_elapsed >= 7 and not await has_followup_sent(booking.id, "1week"):
            message = await generate_followup_message(booking, "1week")
            await push_text(booking.line_user_id, message)
            await log_followup(booking.id, "1week")
            sent_count += 1

    return sent_count


async def generate_followup_message(booking: Booking, followup_type: str) -> str:
    """
    Claude を使ってパーソナライズされたフォローアップメッセージを生成する。
    公開しているためテストでモック可能。
    """
    timing = "3日" if followup_type == "3day" else "1週間"
    notes_section = (
        f"\n体験時のメモ: {booking.trial_notes}"
        if booking.trial_notes
        else ""
    )

    direction = (
        "体験はいかがでしたでしょうか？感想や疑問点があればお気軽にお聞きください"
        "という初回の温かいフォローアップ"
        if followup_type == "3day"
        else "その後ご検討はいかがでしょうか？入塾に向けた背中を押す、丁寧だが前向きな2回目のフォロー"
    )

    prompt = (
        f"以下の体験授業から{timing}が経過しました。保護者へのフォローアップ LINE メッセージを生成してください。\n\n"
        f"生徒名: {booking.student_name}\n"
        f"学年: {booking.grade}\n"
        f"体験科目: {booking.subject}\n"
        f"体験日: {booking.scheduled_at.strftime('%Y年%m月%d日')}{notes_section}\n\n"
        f"【メッセージの方向性】{direction}\n\n"
        f"100〜150文字で塾側からの自然な LINE メッセージとして作成してください。"
    )

    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    response = _claude.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
