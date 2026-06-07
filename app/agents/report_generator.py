"""
授業報告自動生成エージェント。

【フロー】
  1. 講師が LINE に「報告 山田太郎\n授業内容...」と送信
  2. Claude が保護者向けの丁寧な連絡帳文章を生成
  3. 下書きを講師に返す
  4. 講師が「送信」と返信 → 保護者の LINE に自動送信
  5. 「キャンセル」で破棄

ペンディング中の下書きがあるときは新規報告を受け付けない（誤送信防止）。
"""

import os
from typing import Optional, Tuple

import anthropic

from app.database import (
    create_lesson_report,
    get_pending_report,
    get_student_by_name,
    update_report_status,
)
from app.line_client import push_text
from app.models import LessonReport

_claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

_CONFIRM_KEYWORDS = {"送信", "送信する", "ok", "OK", "はい", "yes"}
_CANCEL_KEYWORDS = {"キャンセル", "やり直し", "修正", "cancel"}

_SYSTEM_PROMPT = """あなたは学習塾の連絡帳作成AIです。
講師の授業メモを、保護者に向けた丁寧で温かみのある連絡帳文章に変換してください。

【変換ルール】
- 保護者への敬語を使い、読みやすい文章にする
- お子様の頑張りや良かった点を具体的に伝える
- 改善が必要な点は前向き・建設的に表現する（否定的な言い方を避ける）
- 宿題・次回の目標があれば明記する
- 200〜300文字程度にまとめる
- 署名は不要（システムが後から付加するため）
"""


# ── 公開インターフェース ──────────────────────────────────────────────────


async def process_teacher_message(
    teacher_line_user_id: str, message: str
) -> str:
    """
    講師からのメッセージを処理して返答を返す。
    ペンディング中の下書きがある場合は確認モードで動作する。
    """
    pending = await get_pending_report(teacher_line_user_id)

    # ── 確認モード（下書きがある場合）────────────────────────────────────
    if pending:
        stripped = message.strip()

        if stripped in _CONFIRM_KEYWORDS:
            if pending.parent_line_user_id:
                await push_text(pending.parent_line_user_id, pending.generated_content or "")
            await update_report_status(pending.id, "sent")
            return "✅ 保護者に連絡帳を送信しました！"

        if stripped in _CANCEL_KEYWORDS:
            await update_report_status(pending.id, "cancelled")
            return "キャンセルしました。もう一度「報告 生徒名」から入力してください。"

        # どちらでもない場合は現在の下書きを再提示する
        return (
            f"以下の連絡帳が送信待ちです。\n\n"
            f"---\n{pending.generated_content}\n---\n\n"
            f"「送信」で保護者に送信 / 「キャンセル」でやり直し"
        )

    # ── 新規報告モード ────────────────────────────────────────────────────
    student_name, memo = _parse_report_message(message)

    if not student_name or not memo:
        return (
            "以下の形式で送ってください。\n\n"
            "報告 [生徒名]\n"
            "[授業メモを自由に入力]\n\n"
            "例:\n"
            "報告 山田太郎\n"
            "今日は二次方程式の演習。解の公式は理解できているが"
            "符号ミスが多い。次回は計算の確認習慣を定着させる。"
        )

    # 生徒を DB から検索（見つからなくても続行）
    student = await get_student_by_name(student_name)
    parent_line_user_id = student.line_user_id if student else None

    # Claude で連絡帳を生成
    generated = await _generate_report_text(student_name, memo)

    # DB に下書きを保存
    await create_lesson_report(
        LessonReport(
            student_id=student.id if student else None,
            teacher_line_user_id=teacher_line_user_id,
            raw_content=memo,
            generated_content=generated,
            parent_line_user_id=parent_line_user_id,
        )
    )

    warning = ""
    if not student:
        warning = f"\n\n⚠️ 「{student_name}」が生徒名簿に見つかりませんでした。送信先を確認してください。"

    return (
        f"📝 連絡帳の下書きを作成しました。{warning}\n\n"
        f"---\n{generated}\n---\n\n"
        f"「送信」で保護者に送信 / 「キャンセル」でやり直し"
    )


# ── パース ────────────────────────────────────────────────────────────────


def parse_report_message(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    「報告 [生徒名]\n[メモ]」形式を解析して (生徒名, メモ) を返す。
    形式が不正な場合は (None, None)。
    テスト可能なよう公開している。
    """
    lines = message.strip().split("\n", 1)
    first = lines[0].strip()

    # 「報告」で始まる行が必要
    if not first.startswith("報告"):
        return None, None

    student_name = first[len("報告"):].strip()
    if not student_name:
        return None, None

    memo = lines[1].strip() if len(lines) > 1 else ""
    if not memo:
        return None, None

    return student_name, memo


# モジュール内部でも同じ関数を使う
_parse_report_message = parse_report_message


# ── Claude 呼び出し ───────────────────────────────────────────────────────


async def _generate_report_text(student_name: str, memo: str) -> str:
    """Claude を使って講師メモを保護者向け連絡帳に変換する"""
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    response = _claude.messages.create(
        model=model,
        max_tokens=400,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"生徒名: {student_name}\n\n"
                    f"【講師メモ】\n{memo}\n\n"
                    f"上記を保護者向け連絡帳文章に変換してください。"
                ),
            }
        ],
    )
    return response.content[0].text.strip()
