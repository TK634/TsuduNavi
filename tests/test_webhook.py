"""
webhook.py のエンドポイントテスト。
LINE APIとClaudeはモックして実行する。
"""

import base64
import hashlib
import hmac
import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# テスト用環境変数をセット（import より前に設定する必要がある）
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test_secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test_key")
os.environ.setdefault("GOOGLE_CALENDAR_CREDENTIALS_JSON", '{"type":"service_account"}')
os.environ.setdefault("GOOGLE_CALENDAR_ID", "test@group.calendar.google.com")

from app.main import app  # noqa: E402

client = TestClient(app)


def _make_signature(body: bytes, secret: str = "test_secret") -> str:
    """テスト用のLINE署名を生成する"""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _make_text_event(user_id: str = "U123", text: str = "こんにちは") -> dict:
    """テスト用のLINEテキストメッセージイベントを生成する"""
    return {
        "events": [
            {
                "type": "message",
                "replyToken": "reply_token_xxx",
                "source": {"type": "user", "userId": user_id},
                "message": {"type": "text", "id": "msg_001", "text": text},
            }
        ]
    }


# ── ヘルスチェック ────────────────────────────────────────────────────────


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── 署名検証 ─────────────────────────────────────────────────────────────


def test_webhook_署名なしは400():
    body = json.dumps(_make_text_event()).encode()
    response = client.post(
        "/line/webhook",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_webhook_不正署名は400():
    body = json.dumps(_make_text_event()).encode()
    response = client.post(
        "/line/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": "invalid_signature",
        },
    )
    assert response.status_code == 400


# ── 正常系 ────────────────────────────────────────────────────────────────


@patch("app.webhook.process_message", new_callable=AsyncMock)
@patch("app.webhook.reply_text", new_callable=AsyncMock)
def test_webhook_テキストメッセージ処理(mock_reply, mock_process):
    """正しい署名のリクエストはエージェントに処理委譲される"""
    mock_process.return_value = ("こんにちは！学年を教えてください。", None)

    body = json.dumps(_make_text_event()).encode()
    sig = _make_signature(body)

    response = client.post(
        "/line/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": sig,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_process.assert_called_once()


@patch("app.webhook.process_message", new_callable=AsyncMock)
@patch("app.webhook.reply_with_buttons", new_callable=AsyncMock)
def test_webhook_スロット候補付き返答(mock_buttons, mock_process):
    """スロット候補がある場合はボタン形式で返答する"""
    from datetime import datetime, timedelta

    from app.models import TimeSlot

    now = datetime.now()
    slots = [
        TimeSlot(start=now + timedelta(days=1), end=now + timedelta(days=1, hours=1)),
        TimeSlot(start=now + timedelta(days=2), end=now + timedelta(days=2, hours=1)),
    ]
    mock_process.return_value = ("以下の日程はいかがでしょうか？", slots)

    body = json.dumps(_make_text_event(text="水曜の午後")).encode()
    sig = _make_signature(body)

    response = client.post(
        "/line/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": sig,
        },
    )
    assert response.status_code == 200
    mock_buttons.assert_called_once()


def test_webhook_テキスト以外のイベントは無視される():
    """スタンプや画像など、テキスト以外のメッセージは処理せずに200を返す"""
    body = json.dumps({
        "events": [
            {
                "type": "message",
                "replyToken": "token_xxx",
                "source": {"type": "user", "userId": "U123"},
                "message": {"type": "image", "id": "img_001"},
            }
        ]
    }).encode()
    sig = _make_signature(body)

    response = client.post(
        "/line/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": sig,
        },
    )
    assert response.status_code == 200
