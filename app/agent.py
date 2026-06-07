"""
会話ステートマシン + Claude APIによるヒアリングフロー。

ステージ遷移:
  greeting → collect_grade → collect_subject → collect_schedule
  → show_slots → confirm_booking → completed
"""

import os
import re
from datetime import datetime
from typing import List, Optional, Tuple

import anthropic

from app.calendar import create_calendar_event, get_available_slots
from app.database import (
    create_booking,
    get_conversation,
    save_conversation,
    upsert_student,
)
from app.models import (
    Booking,
    CollectedData,
    ConversationStage,
    ConversationState,
    Message,
    Student,
    TimeSlot,
)

_claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

_SYSTEM_PROMPT = """あなたはツヅナビです。学習塾の体験授業予約をサポートするAIアシスタントです。
保護者が体験授業を予約できるようサポートしてください。

【ヒアリング項目（この順番で収集）】
1. お子様の学年（例: 小3、中2、高1）
2. 体験希望の科目（国語・算数/数学・英語・理科・社会）
3. 希望の曜日と時間帯（午前/午後/夕方/夜）

【返答ルール】
- 常に丁寧・親切なトーンで、80文字以内の短い文章
- 収集済みの情報は再度聞かない
- スロット選択フェーズではボタンで対応するため案内のみ行う
- 予約確定後はお礼と確認メッセージを送る
"""


# ── 公開インターフェース ──────────────────────────────────────────────────


async def process_message(
    line_user_id: str,
    user_message: str,
) -> Tuple[str, Optional[List[TimeSlot]]]:
    """
    LINEユーザーのメッセージを受け取り、返答テキストと
    スロット候補リスト（show_slots ステージのみ）を返す。
    """
    state = await get_conversation(line_user_id) or ConversationState(
        line_user_id=line_user_id
    )

    # ユーザーメッセージを履歴に追加
    state.messages.append(
        Message(role="user", content=user_message, timestamp=datetime.now().isoformat())
    )

    response_text, slots = await _process_stage(state, user_message)

    state.messages.append(
        Message(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat(),
        )
    )
    await save_conversation(state)

    return response_text, slots


# ── ステージ処理 ──────────────────────────────────────────────────────────


async def _process_stage(
    state: ConversationState, user_message: str
) -> Tuple[str, Optional[List[TimeSlot]]]:
    """現在のステージに応じた処理を行い、返答とスロット候補を返す"""

    # ── GREETING: 最初の挨拶 ──────────────────────────────────────────────
    if state.stage == ConversationStage.GREETING:
        state.stage = ConversationStage.COLLECT_GRADE
        return await _ask_claude(state, "まず挨拶をして、お子様の学年を聞いてください。"), None

    # ── COLLECT_GRADE: 学年収集 ───────────────────────────────────────────
    if state.stage == ConversationStage.COLLECT_GRADE:
        grade = _extract_grade(user_message)
        if grade:
            state.collected_data.grade = grade
            state.stage = ConversationStage.COLLECT_SUBJECT
            instruction = f"{grade}ですね。ありがとうございます。希望の科目を聞いてください。"
        else:
            instruction = "学年が読み取れませんでした。もう一度お子様の学年を聞いてください。"
        return await _ask_claude(state, instruction), None

    # ── COLLECT_SUBJECT: 科目収集 ─────────────────────────────────────────
    if state.stage == ConversationStage.COLLECT_SUBJECT:
        subject = _extract_subject(user_message)
        if subject:
            state.collected_data.subject = subject
            state.stage = ConversationStage.COLLECT_SCHEDULE
            instruction = f"{subject}ですね。ご希望の曜日と時間帯（午前/午後/夕方/夜）を聞いてください。"
        else:
            instruction = "科目が読み取れませんでした。希望の科目（国語・算数・数学・英語・理科・社会）を聞いてください。"
        return await _ask_claude(state, instruction), None

    # ── COLLECT_SCHEDULE: 希望日程収集 ───────────────────────────────────
    if state.stage == ConversationStage.COLLECT_SCHEDULE:
        days, time = _extract_schedule(user_message)
        state.collected_data.preferred_days = days
        state.collected_data.preferred_time = time or "午後"
        state.stage = ConversationStage.SHOW_SLOTS
        instruction = "空き時間を確認する旨を伝えて、少々お待ちくださいと言ってください。"
        text = await _ask_claude(state, instruction)

        # 空きスロットを取得して保存
        slots = await get_available_slots(
            preferred_days=state.collected_data.preferred_days or [],
            preferred_time=state.collected_data.preferred_time,
        )
        state.collected_data.available_slots = [s.to_dict() for s in slots]

        if not slots:
            state.stage = ConversationStage.COLLECT_SCHEDULE
            return "申し訳ありません。ご希望の日程に空きが見つかりませんでした。別の曜日や時間帯はいかがでしょうか？", None

        return text, slots

    # ── SHOW_SLOTS: スロット選択待ち ──────────────────────────────────────
    if state.stage == ConversationStage.SHOW_SLOTS:
        idx = _extract_slot_selection(user_message)
        slots_data = state.collected_data.available_slots or []

        if idx is None or idx >= len(slots_data):
            return "①②③の番号でお選びいただくか、もう一度ご希望の曜日をお聞かせください。", None

        state.collected_data.selected_slot_index = idx
        state.stage = ConversationStage.CONFIRM_BOOKING

        selected = TimeSlot.from_dict(slots_data[idx])
        day_names = ["月", "火", "水", "木", "金", "土", "日"]
        day = day_names[selected.start.weekday()]
        slot_str = (
            f"{selected.start.month}月{selected.start.day}日（{day}）"
            f"{selected.start.strftime('%H:%M')}〜{selected.end.strftime('%H:%M')}"
        )

        # カレンダー登録・DB保存・生徒情報更新
        event_id = await create_calendar_event(
            student_name=state.collected_data.student_name or "お子様",
            grade=state.collected_data.grade or "",
            subject=state.collected_data.subject or "",
            slot=selected,
        )

        booking = await create_booking(
            Booking(
                line_user_id=state.line_user_id,
                student_name=state.collected_data.student_name or "お子様",
                grade=state.collected_data.grade or "",
                subject=state.collected_data.subject or "",
                scheduled_at=selected.start,
                calendar_event_id=event_id,
            )
        )

        # 生徒情報をSupabaseに保存・更新する
        await upsert_student(
            Student(
                line_user_id=state.line_user_id,
                grade=state.collected_data.grade,
                name=state.collected_data.student_name,
            )
        )

        state.stage = ConversationStage.COMPLETED
        return (
            f"✅ 予約が確定しました！\n"
            f"【日時】{slot_str}\n"
            f"【科目】{state.collected_data.subject}\n"
            f"【学年】{state.collected_data.grade}\n\n"
            f"当日お待ちしております。ご不明な点はいつでもご連絡ください。"
        ), None

    # ── COMPLETED: 予約完了後 ─────────────────────────────────────────────
    if state.stage == ConversationStage.COMPLETED:
        return "ご予約は完了しています。何かご不明な点があればお気軽にお声がけください😊", None

    return "申し訳ありません。エラーが発生しました。もう一度お試しください。", None


# ── Claude API呼び出し ────────────────────────────────────────────────────


async def _ask_claude(state: ConversationState, instruction: str) -> str:
    """
    会話履歴全体をコンテキストとしてClaudeに渡し、返答を生成する。
    instruction で今回の返答方針を指示する。
    """
    system = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"【収集済み情報】\n{_format_collected(state.collected_data)}\n\n"
        f"【今回の指示】{instruction}\n"
        f"返答は日本語で80文字以内にしてください。"
    )

    # 会話履歴（最新のユーザーメッセージは含む）
    messages = [
        {"role": m.role, "content": m.content}
        for m in state.messages
        if m.role in ("user", "assistant")
    ]
    # 履歴が空の場合はダミーのユーザーメッセージを追加
    if not messages:
        messages = [{"role": "user", "content": "こんにちは"}]

    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    response = _claude.messages.create(
        model=model,
        max_tokens=200,
        system=system,
        messages=messages,
    )
    return response.content[0].text.strip()


# ── 情報抽出ヘルパー ─────────────────────────────────────────────────────


def _extract_grade(text: str) -> Optional[str]:
    """テキストから学年を抽出する"""
    # 正規化パターン
    patterns = [
        (r"小学?(\d)[年生]", lambda m: f"小{m.group(1)}"),
        (r"中学?(\d)[年生]", lambda m: f"中{m.group(1)}"),
        (r"高校?(\d)[年生]", lambda m: f"高{m.group(1)}"),
    ]
    for pattern, formatter in patterns:
        m = re.search(pattern, text)
        if m:
            return formatter(m)

    # 短縮形（小3、中2 など）
    m = re.search(r"[小中高](\d)", text)
    if m:
        return m.group(0)

    return None


def _extract_subject(text: str) -> Optional[str]:
    """テキストから科目を抽出する"""
    subjects = ["国語", "数学", "算数", "英語", "英会話", "理科", "社会"]
    for subject in subjects:
        if subject in text:
            return subject
    return None


def _extract_schedule(text: str) -> Tuple[List[str], Optional[str]]:
    """テキストから希望曜日リストと時間帯を抽出する"""
    day_keys = ["月", "火", "水", "木", "金", "土", "日"]
    days = [d for d in day_keys if d in text]

    time = None
    for keyword, label in [
        ("夜", "夜"), ("夕方", "夕方"), ("夕", "夕方"),
        ("午前", "午前"), ("朝", "午前"),
        ("午後", "午後"), ("昼", "午後"),
    ]:
        if keyword in text:
            time = label
            break

    return days, time


def _extract_slot_selection(text: str) -> Optional[int]:
    """ユーザーのスロット選択（①②③ or 1/2/3番）を 0-based インデックスで返す"""
    if "①" in text or re.search(r"\b1\b|1番|1つ目|第1", text):
        return 0
    if "②" in text or re.search(r"\b2\b|2番|2つ目|第2", text):
        return 1
    if "③" in text or re.search(r"\b3\b|3番|3つ目|第3", text):
        return 2
    return None


def _format_collected(data: CollectedData) -> str:
    """収集済みデータを読みやすい形式にフォーマットする"""
    lines = []
    if data.grade:
        lines.append(f"・学年: {data.grade}")
    if data.subject:
        lines.append(f"・科目: {data.subject}")
    if data.preferred_days:
        lines.append(f"・希望曜日: {'・'.join(data.preferred_days)}")
    if data.preferred_time:
        lines.append(f"・希望時間帯: {data.preferred_time}")
    return "\n".join(lines) if lines else "（未収集）"
