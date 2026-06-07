import os
from datetime import datetime, timedelta
from typing import List, Optional

from supabase import Client, create_client

from app.models import (
    Booking,
    CollectedData,
    ContactLog,
    ConversationStage,
    ConversationState,
    FollowupLog,
    Invoice,
    LessonReport,
    Message,
    ReminderLog,
    Student,
    Teacher,
)


def get_supabase_client() -> Client:
    """Supabaseクライアントを初期化して返す"""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def _row_to_student(row: dict) -> Student:
    return Student(
        id=row["id"],
        line_user_id=row.get("line_user_id"),
        name=row.get("name"),
        grade=row.get("grade"),
        risk_score=float(row.get("risk_score") or 0),
        risk_level=row.get("risk_level", "low"),
        created_at=row.get("created_at"),
    )


def _row_to_booking(row: dict) -> Booking:
    return Booking(
        id=row["id"],
        line_user_id=row["line_user_id"],
        student_name=row["student_name"],
        grade=row["grade"],
        subject=row["subject"],
        scheduled_at=datetime.fromisoformat(row["scheduled_at"]),
        calendar_event_id=row.get("calendar_event_id"),
        status=row["status"],
        trial_notes=row.get("trial_notes"),
        trial_completed_at=(
            datetime.fromisoformat(row["trial_completed_at"])
            if row.get("trial_completed_at")
            else None
        ),
        created_at=row.get("created_at"),
    )


# ── 会話状態 ──────────────────────────────────────────────────────────────


async def get_conversation(line_user_id: str) -> Optional[ConversationState]:
    """LINEユーザーIDで会話状態を取得する"""
    client = get_supabase_client()
    result = (
        client.table("conversations")
        .select("*")
        .eq("line_user_id", line_user_id)
        .execute()
    )
    if not result.data:
        return None

    row = result.data[0]
    return ConversationState(
        id=row["id"],
        line_user_id=row["line_user_id"],
        stage=ConversationStage(row["stage"]),
        collected_data=CollectedData(**(row["collected_data"] or {})),
        messages=[Message(**m) for m in (row["messages"] or [])],
        updated_at=row.get("updated_at"),
    )


async def save_conversation(state: ConversationState) -> ConversationState:
    """会話状態をSupabaseに保存（存在すれば更新、なければ挿入）する"""
    client = get_supabase_client()
    data = {
        "line_user_id": state.line_user_id,
        "stage": state.stage.value,
        "collected_data": state.collected_data.model_dump(),
        "messages": [m.model_dump() for m in state.messages],
        "updated_at": datetime.now().isoformat(),
    }

    if state.id:
        result = client.table("conversations").update(data).eq("id", state.id).execute()
    else:
        result = client.table("conversations").insert(data).execute()

    if result.data:
        state.id = result.data[0]["id"]
    return state


async def reset_conversation(line_user_id: str) -> None:
    """会話をリセットする（再ヒアリング用）"""
    client = get_supabase_client()
    client.table("conversations").delete().eq("line_user_id", line_user_id).execute()


# ── 生徒情報 ──────────────────────────────────────────────────────────────


async def get_student(line_user_id: str) -> Optional[Student]:
    """LINEユーザーIDで生徒（保護者）情報を取得する"""
    client = get_supabase_client()
    result = (
        client.table("students")
        .select("*")
        .eq("line_user_id", line_user_id)
        .execute()
    )
    if not result.data:
        return None
    return _row_to_student(result.data[0])


async def get_student_by_id(student_id: str) -> Optional[Student]:
    """UUIDで生徒情報を取得する"""
    client = get_supabase_client()
    result = client.table("students").select("*").eq("id", student_id).execute()
    if not result.data:
        return None
    return _row_to_student(result.data[0])


async def get_student_by_name(name: str) -> Optional[Student]:
    """氏名（部分一致）で生徒情報を取得する"""
    client = get_supabase_client()
    result = (
        client.table("students")
        .select("*")
        .ilike("name", f"%{name}%")
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return _row_to_student(result.data[0])


async def get_all_students() -> List[Student]:
    """全生徒情報を取得する（退塾リスク検知バッチ用）"""
    client = get_supabase_client()
    result = client.table("students").select("*").execute()
    return [_row_to_student(row) for row in result.data]


async def upsert_student(student: Student) -> Student:
    """生徒情報を保存（存在すれば更新、なければ挿入）する"""
    client = get_supabase_client()
    data: dict = {"name": student.name, "grade": student.grade}
    if student.line_user_id:
        data["line_user_id"] = student.line_user_id

    existing = None
    if student.line_user_id:
        existing = (
            client.table("students")
            .select("id")
            .eq("line_user_id", student.line_user_id)
            .execute()
        )

    if existing and existing.data:
        result = (
            client.table("students")
            .update(data)
            .eq("line_user_id", student.line_user_id)
            .execute()
        )
    else:
        result = client.table("students").insert(data).execute()

    if result.data:
        student.id = result.data[0]["id"]
    return student


async def update_student_risk(student_id: str, score: float, level: str) -> None:
    """退塾リスクスコアを更新する"""
    client = get_supabase_client()
    client.table("students").update(
        {"risk_score": score, "risk_level": level}
    ).eq("id", student_id).execute()


# ── 講師 ──────────────────────────────────────────────────────────────────


async def is_teacher(line_user_id: str) -> bool:
    """LINEユーザーIDが講師テーブルに登録されているか確認する"""
    client = get_supabase_client()
    result = (
        client.table("teachers")
        .select("id")
        .eq("line_user_id", line_user_id)
        .execute()
    )
    return bool(result.data)


# ── 予約 ──────────────────────────────────────────────────────────────────


async def create_booking(booking: Booking) -> Booking:
    """予約情報をSupabaseに作成する"""
    client = get_supabase_client()
    data = {
        "line_user_id": booking.line_user_id,
        "student_name": booking.student_name,
        "grade": booking.grade,
        "subject": booking.subject,
        "scheduled_at": booking.scheduled_at.isoformat(),
        "calendar_event_id": booking.calendar_event_id,
        "status": booking.status,
    }
    result = client.table("bookings").insert(data).execute()
    if result.data:
        booking.id = result.data[0]["id"]
    return booking


async def get_bookings_by_user(line_user_id: str) -> List[Booking]:
    """LINEユーザーIDで予約一覧を取得する"""
    client = get_supabase_client()
    result = (
        client.table("bookings")
        .select("*")
        .eq("line_user_id", line_user_id)
        .execute()
    )
    return [_row_to_booking(row) for row in result.data]


async def get_completed_trials_for_followup() -> List[Booking]:
    """
    フォローアップ対象の体験授業完了レコードを取得する。
    trial_completed_at が過去2週間以内のものを対象とする。
    """
    client = get_supabase_client()
    two_weeks_ago = (datetime.now() - timedelta(weeks=2)).isoformat()
    result = (
        client.table("bookings")
        .select("*")
        # NULLは >= 比較で自動除外される
        .gte("trial_completed_at", two_weeks_ago)
        .execute()
    )
    return [_row_to_booking(row) for row in result.data]


# ── 退塾リスク（出席・成績・連絡ログ）────────────────────────────────────


async def get_recent_attendances(student_id: str, weeks: int = 4) -> List[dict]:
    """直近 N 週間の出席記録を取得する"""
    client = get_supabase_client()
    from datetime import date, timedelta

    since = (date.today() - timedelta(weeks=weeks)).isoformat()
    result = (
        client.table("attendances")
        .select("attended")
        .eq("student_id", student_id)
        .gte("lesson_date", since)
        .execute()
    )
    return result.data


async def get_recent_grades(student_id: str, limit: int = 2) -> List[dict]:
    """直近 N 件の成績を新しい順に取得する"""
    client = get_supabase_client()
    result = (
        client.table("grades")
        .select("score, test_date")
        .eq("student_id", student_id)
        .order("test_date", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


async def get_last_contact(student_id: str) -> Optional[datetime]:
    """最終連絡日時を取得する。記録がなければ None を返す"""
    client = get_supabase_client()
    result = (
        client.table("contact_logs")
        .select("contacted_at")
        .eq("student_id", student_id)
        .order("contacted_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    raw = result.data[0]["contacted_at"].replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    return dt.replace(tzinfo=None)


# ── 授業報告 ──────────────────────────────────────────────────────────────


async def get_pending_report(teacher_line_user_id: str) -> Optional[LessonReport]:
    """講師の未送信（draft）報告を最新1件取得する"""
    client = get_supabase_client()
    result = (
        client.table("lesson_reports")
        .select("*")
        .eq("teacher_line_user_id", teacher_line_user_id)
        .eq("status", "draft")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    return LessonReport(
        id=row["id"],
        student_id=row.get("student_id"),
        teacher_line_user_id=row["teacher_line_user_id"],
        raw_content=row["raw_content"],
        generated_content=row.get("generated_content"),
        status=row["status"],
        parent_line_user_id=row.get("parent_line_user_id"),
        created_at=row.get("created_at"),
    )


async def create_lesson_report(report: LessonReport) -> LessonReport:
    """授業報告をSupabaseに作成する"""
    client = get_supabase_client()
    data = {
        "student_id": report.student_id,
        "teacher_line_user_id": report.teacher_line_user_id,
        "raw_content": report.raw_content,
        "generated_content": report.generated_content,
        "status": report.status,
        "parent_line_user_id": report.parent_line_user_id,
    }
    result = client.table("lesson_reports").insert(data).execute()
    if result.data:
        report.id = result.data[0]["id"]
    return report


async def update_report_status(report_id: str, status: str) -> None:
    """授業報告のステータスを更新する"""
    client = get_supabase_client()
    client.table("lesson_reports").update({"status": status}).eq("id", report_id).execute()


# ── 月謝・請求 ────────────────────────────────────────────────────────────


async def get_unpaid_invoices() -> List[Invoice]:
    """未払い（pending / overdue）の請求を全件取得する"""
    client = get_supabase_client()
    result = (
        client.table("invoices")
        .select("*")
        .in_("status", ["pending", "overdue"])
        .execute()
    )
    invoices = []
    from datetime import date

    for row in result.data:
        invoices.append(
            Invoice(
                id=row["id"],
                student_id=row["student_id"],
                line_user_id=row["line_user_id"],
                amount=row["amount"],
                due_date=date.fromisoformat(row["due_date"]),
                paid_at=row.get("paid_at"),
                status=row["status"],
                month=row["month"],
                created_at=row.get("created_at"),
            )
        )
    return invoices


async def has_reminder_sent(invoice_id: str, reminder_type: str) -> bool:
    """指定タイプのリマインドをすでに送信済みか確認する"""
    client = get_supabase_client()
    result = (
        client.table("reminder_logs")
        .select("id")
        .eq("invoice_id", invoice_id)
        .eq("reminder_type", reminder_type)
        .execute()
    )
    return bool(result.data)


async def log_reminder(invoice_id: str, reminder_type: str) -> None:
    """リマインド送信履歴を記録する"""
    client = get_supabase_client()
    client.table("reminder_logs").insert(
        {
            "invoice_id": invoice_id,
            "reminder_type": reminder_type,
            "sent_at": datetime.now().isoformat(),
        }
    ).execute()


# ── 体験フォローアップ ────────────────────────────────────────────────────


async def has_followup_sent(booking_id: str, followup_type: str) -> bool:
    """指定タイプのフォローアップをすでに送信済みか確認する"""
    client = get_supabase_client()
    result = (
        client.table("followup_logs")
        .select("id")
        .eq("booking_id", booking_id)
        .eq("followup_type", followup_type)
        .execute()
    )
    return bool(result.data)


async def log_followup(booking_id: str, followup_type: str) -> None:
    """フォローアップ送信履歴を記録する"""
    client = get_supabase_client()
    client.table("followup_logs").insert(
        {
            "booking_id": booking_id,
            "followup_type": followup_type,
            "sent_at": datetime.now().isoformat(),
        }
    ).execute()
