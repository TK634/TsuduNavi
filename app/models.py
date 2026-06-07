from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── 予約・会話フロー ──────────────────────────────────────────────────────


class ConversationStage(str, Enum):
    GREETING = "greeting"
    COLLECT_GRADE = "collect_grade"
    COLLECT_SUBJECT = "collect_subject"
    COLLECT_SCHEDULE = "collect_schedule"
    SHOW_SLOTS = "show_slots"
    CONFIRM_BOOKING = "confirm_booking"
    COMPLETED = "completed"


class Message(BaseModel):
    role: str  # "user" または "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class CollectedData(BaseModel):
    student_name: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    preferred_days: Optional[List[str]] = None
    preferred_time: Optional[str] = None
    available_slots: Optional[List[Dict[str, str]]] = None
    selected_slot_index: Optional[int] = None


class ConversationState(BaseModel):
    id: Optional[str] = None
    line_user_id: str
    stage: ConversationStage = ConversationStage.GREETING
    collected_data: CollectedData = Field(default_factory=CollectedData)
    messages: List[Message] = Field(default_factory=list)
    updated_at: Optional[str] = None


# ── 生徒・講師 ────────────────────────────────────────────────────────────


class Student(BaseModel):
    id: Optional[str] = None
    line_user_id: Optional[str] = None
    name: Optional[str] = None
    grade: Optional[str] = None
    risk_score: float = 0.0
    risk_level: str = "low"  # low / medium / high
    created_at: Optional[str] = None


class Teacher(BaseModel):
    id: Optional[str] = None
    line_user_id: str
    name: Optional[str] = None
    created_at: Optional[str] = None


# ── 予約・体験授業 ────────────────────────────────────────────────────────


class Booking(BaseModel):
    id: Optional[str] = None
    line_user_id: str
    student_name: str
    grade: str
    subject: str
    scheduled_at: datetime
    calendar_event_id: Optional[str] = None
    status: str = "confirmed"
    trial_notes: Optional[str] = None          # 体験時のメモ
    trial_completed_at: Optional[datetime] = None  # 体験完了日時
    created_at: Optional[str] = None


class TimeSlot(BaseModel):
    start: datetime
    end: datetime

    def to_dict(self) -> Dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "TimeSlot":
        return cls(
            start=datetime.fromisoformat(d["start"]),
            end=datetime.fromisoformat(d["end"]),
        )


# ── 退塾リスク ────────────────────────────────────────────────────────────


class RiskResult(BaseModel):
    student_id: str
    student_name: Optional[str]
    score: float                  # 0〜100
    level: str                    # low / medium / high
    attendance_score: float       # 出席率スコア（最大40）
    grade_score: float            # 成績スコア（最大35）
    contact_score: float          # 連絡スコア（最大25）


class Attendance(BaseModel):
    id: Optional[str] = None
    student_id: str
    lesson_date: date
    attended: bool = True
    subject: Optional[str] = None
    teacher_line_user_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


class Grade(BaseModel):
    id: Optional[str] = None
    student_id: str
    subject: str
    score: float
    test_date: date
    test_type: Optional[str] = None
    created_at: Optional[str] = None


class ContactLog(BaseModel):
    id: Optional[str] = None
    student_id: str
    contacted_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    contact_type: str = "line"  # line / phone / face_to_face
    notes: Optional[str] = None


# ── 授業報告 ──────────────────────────────────────────────────────────────


class LessonReport(BaseModel):
    id: Optional[str] = None
    student_id: Optional[str] = None
    teacher_line_user_id: str
    raw_content: str             # 講師の生メモ
    generated_content: Optional[str] = None  # Claude生成の丁寧な文章
    status: str = "draft"        # draft / sent / cancelled
    parent_line_user_id: Optional[str] = None
    created_at: Optional[str] = None


# ── 月謝・請求 ────────────────────────────────────────────────────────────


class Invoice(BaseModel):
    id: Optional[str] = None
    student_id: str
    line_user_id: str            # 保護者の LINE ID（JOIN不要のため非正規化）
    amount: int                  # 円
    due_date: date
    paid_at: Optional[str] = None
    status: str = "pending"      # pending / paid / overdue
    month: str                   # '2026-06' 形式
    created_at: Optional[str] = None


class ReminderLog(BaseModel):
    id: Optional[str] = None
    invoice_id: str
    sent_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    reminder_type: str           # 3days_before / due_day / 3days_after


class FollowupLog(BaseModel):
    id: Optional[str] = None
    booking_id: str
    followup_type: str           # 3day / 1week
    sent_at: str = Field(default_factory=lambda: datetime.now().isoformat())
