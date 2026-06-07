"""
月謝リマインドエージェント。

【送信タイミングと文体】
  3日前: 丁寧なお知らせ
  当日 : 通常の催促
  3日後: 丁寧だが強めの催促

重複送信防止のため reminder_logs テーブルで送信済みを管理する。
"""

from datetime import date
from typing import Optional

from app.database import (
    get_unpaid_invoices,
    has_reminder_sent,
    log_reminder,
)
from app.line_client import push_text
from app.models import Invoice

# 段階別メッセージテンプレート
_TEMPLATES: dict[str, str] = {
    "3days_before": (
        "いつもお世話になっております。\n"
        "{month}分の月謝（{amount}円）のお支払い期日が{due_date}に迫っております。\n"
        "お手続きのご確認をよろしくお願いいたします。"
    ),
    "due_day": (
        "いつもお世話になっております。\n"
        "本日は{month}分の月謝（{amount}円）のお支払い期日です。\n"
        "まだのご場合は、本日中にお手続きをお願いいたします。"
    ),
    "3days_after": (
        "いつもお世話になっております。\n"
        "{month}分の月謝（{amount}円）のご入金が確認できておりません。\n"
        "お手続きがお済みでない場合は、至急ご対応をお願いいたします。\n"
        "ご不明な点がございましたらお気軽に塾までご連絡ください。"
    ),
}


# ── 公開インターフェース ──────────────────────────────────────────────────


async def run_payment_reminders() -> int:
    """
    未払い請求を確認し、タイミングに応じたリマインドを送信する。
    戻り値: 実際に送信した件数。
    """
    today = date.today()
    invoices = await get_unpaid_invoices()
    sent_count = 0

    for invoice in invoices:
        reminder_type = determine_reminder_type(invoice.due_date, today)
        if not reminder_type:
            continue

        # 同じリマインドをすでに送信済みならスキップ
        if await has_reminder_sent(invoice.id, reminder_type):
            continue

        message = build_reminder_message(reminder_type, invoice)
        await push_text(invoice.line_user_id, message)
        await log_reminder(invoice.id, reminder_type)
        sent_count += 1

    return sent_count


# ── 純粋関数（テスト可能に公開）─────────────────────────────────────────


def determine_reminder_type(due_date: date, today: date) -> Optional[str]:
    """
    期日と今日の差分からリマインドの種類を決定する。
    送信対象外の日付の場合は None を返す。
    """
    diff = (due_date - today).days
    if diff == 3:
        return "3days_before"
    if diff == 0:
        return "due_day"
    if diff == -3:
        return "3days_after"
    return None


def build_reminder_message(reminder_type: str, invoice: Invoice) -> str:
    """リマインドメッセージを組み立てる"""
    template = _TEMPLATES[reminder_type]
    return template.format(
        month=invoice.month,
        amount=f"{invoice.amount:,}",
        due_date=invoice.due_date.strftime("%-m月%-d日"),
    )
