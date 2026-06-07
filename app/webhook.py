"""
LINE Messaging API の Webhook エンドポイント。
"""

import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.agent import process_message
from app.agents.report_generator import process_teacher_message
from app.database import is_teacher
from app.line_client import reply_text, reply_with_buttons, verify_line_signature
from app.models import TimeSlot

router = APIRouter()


@router.post("/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(None),
) -> dict[str, Any]:
    """
    LINE Messaging API の Webhook を受信する。
    X-Line-Signature ヘッダーで署名検証を行い、改ざんを防ぐ。
    """
    body = await request.body()

    if not x_line_signature:
        raise HTTPException(status_code=400, detail="X-Line-Signature header is missing")

    if not verify_line_signature(body, x_line_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    body_json = json.loads(body.decode("utf-8"))
    events = body_json.get("events", [])

    for event in events:
        # テキストメッセージイベントのみ処理する
        if event.get("type") != "message":
            continue
        if event.get("message", {}).get("type") != "text":
            continue

        line_user_id: str = event["source"]["userId"]
        user_message: str = event["message"]["text"]
        reply_token: str = event["replyToken"]

        # 講師か保護者かを判定してルーティング
        if await is_teacher(line_user_id):
            response_text = await process_teacher_message(line_user_id, user_message)
            await reply_text(reply_token, response_text)
        else:
            response_text, slots = await process_message(
                line_user_id=line_user_id,
                user_message=user_message,
            )
            if slots:
                await _reply_with_slot_buttons(reply_token, response_text, slots)
            else:
                await reply_text(reply_token, response_text)

    return {"status": "ok"}


async def _reply_with_slot_buttons(
    reply_token: str, text: str, slots: list[TimeSlot]
) -> None:
    """空きスロット候補をボタン形式でリプライ送信する"""
    NUMBERS = ["①", "②", "③"]
    day_names = ["月", "火", "水", "木", "金", "土", "日"]

    buttons = []
    for i, slot in enumerate(slots[:3]):
        day = day_names[slot.start.weekday()]
        label = (
            f"{NUMBERS[i]}"
            f"{slot.start.month}/{slot.start.day}({day})"
            f" {slot.start.strftime('%H:%M')}"
        )
        buttons.append({"label": label[:20], "text": f"{NUMBERS[i]}を希望します"})

    await reply_with_buttons(
        reply_token=reply_token,
        title="空き日程を選んでください",
        text=_format_slot_text(slots),
        buttons=buttons,
    )


def _format_slot_text(slots: list[TimeSlot]) -> str:
    """スロット一覧を alt_text / テンプレート本文用のテキストにフォーマットする"""
    NUMBERS = ["①", "②", "③"]
    day_names = ["月", "火", "水", "木", "金", "土", "日"]
    lines = []
    for i, slot in enumerate(slots[:3]):
        day = day_names[slot.start.weekday()]
        lines.append(
            f"{NUMBERS[i]} {slot.start.month}月{slot.start.day}日({day})"
            f" {slot.start.strftime('%H:%M')}〜{slot.end.strftime('%H:%M')}"
        )
    return "\n".join(lines)
