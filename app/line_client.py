import base64
import hashlib
import hmac
import os
from typing import List

from linebot.v3.messaging import (
    ApiClient,
    ButtonsTemplate,
    Configuration,
    MessageAction,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TemplateMessage,
    TextMessage,
)


def _get_api() -> MessagingApi:
    """LINE Messaging APIクライアントを初期化する"""
    config = Configuration(
        access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    )
    return MessagingApi(ApiClient(config))


def verify_line_signature(body: bytes, signature: str) -> bool:
    """LINE Webhookの署名を検証する（改ざん防止）"""
    channel_secret = os.environ["LINE_CHANNEL_SECRET"].encode("utf-8")
    digest = hmac.new(channel_secret, body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


async def reply_text(reply_token: str, text: str) -> None:
    """テキストメッセージをリプライ送信する"""
    api = _get_api()
    api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=text)],
        )
    )


async def push_text(user_id: str, text: str) -> None:
    """テキストメッセージをプッシュ送信する"""
    api = _get_api()
    api.push_message(
        PushMessageRequest(
            to=user_id,
            messages=[TextMessage(text=text)],
        )
    )


async def reply_with_buttons(
    reply_token: str,
    text: str,
    buttons: List[dict],
    title: str = "日程を選択してください",
) -> None:
    """
    ボタン付きテンプレートメッセージをリプライ送信する。
    buttons は [{"label": "表示名", "text": "送信テキスト"}, ...] の形式（最大4件）。
    """
    api = _get_api()
    actions = [
        MessageAction(label=btn["label"][:20], text=btn["text"])
        for btn in buttons[:4]
    ]
    template = ButtonsTemplate(
        title=title[:40],
        text=text[:60],
        actions=actions,
    )
    api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[
                TemplateMessage(alt_text=text, template=template)
            ],
        )
    )
