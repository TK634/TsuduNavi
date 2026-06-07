import json
import os
from datetime import datetime, timedelta
from typing import List

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.models import TimeSlot

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# 曜日名 → Python weekday() 対応表
_DAY_MAP = {
    "月": 0, "月曜": 0, "月曜日": 0,
    "火": 1, "火曜": 1, "火曜日": 1,
    "水": 2, "水曜": 2, "水曜日": 2,
    "木": 3, "木曜": 3, "木曜日": 3,
    "金": 4, "金曜": 4, "金曜日": 4,
    "土": 5, "土曜": 5, "土曜日": 5,
    "日": 6, "日曜": 6, "日曜日": 6,
}

# 時間帯キーワード → 開始時刻リスト
_TIME_HOURS = {
    "午前": [9, 10, 11],
    "午後": [13, 14, 15, 16],
    "夕方": [16, 17, 18],
    "夜":   [19, 20],
}


def _get_service():
    """Google Calendar APIサービスオブジェクトを初期化する"""
    credentials_json = os.environ["GOOGLE_CALENDAR_CREDENTIALS_JSON"]
    info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=credentials)


async def get_available_slots(
    preferred_days: List[str],
    preferred_time: str,
    duration_minutes: int = 60,
    max_slots: int = 3,
) -> List[TimeSlot]:
    """
    希望曜日・時間帯に合う空きスロットを最大 max_slots 件返す。
    既存カレンダーイベントと重複しないスロットのみを候補とする。
    """
    service = _get_service()
    calendar_id = os.environ["GOOGLE_CALENDAR_ID"]

    now = datetime.now().replace(second=0, microsecond=0)
    time_min = now.isoformat() + "Z"
    time_max = (now + timedelta(days=14)).isoformat() + "Z"

    # 既存イベントを取得して重複チェックに使う
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    existing = result.get("items", [])

    # 希望曜日の weekday 番号セット（未指定なら全曜日）
    target_weekdays = {
        _DAY_MAP[d] for d in preferred_days if d in _DAY_MAP
    }

    # 希望時間帯に対応する開始時刻リスト（マッチしなければ午後デフォルト）
    candidate_hours = _TIME_HOURS.get(preferred_time, _TIME_HOURS["午後"])

    slots: List[TimeSlot] = []

    for day_offset in range(14):
        check_date = (now + timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if target_weekdays and check_date.weekday() not in target_weekdays:
            continue

        for hour in candidate_hours:
            slot_start = check_date.replace(hour=hour)
            slot_end = slot_start + timedelta(minutes=duration_minutes)

            if slot_start <= now:
                continue

            # 既存イベントとの重複チェック
            overlaps = False
            for event in existing:
                s_str = event["start"].get("dateTime", event["start"].get("date", ""))
                e_str = event["end"].get("dateTime", event["end"].get("date", ""))
                try:
                    ev_start = datetime.fromisoformat(
                        s_str.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    ev_end = datetime.fromisoformat(
                        e_str.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except ValueError:
                    continue
                if slot_start < ev_end and slot_end > ev_start:
                    overlaps = True
                    break

            if not overlaps:
                slots.append(TimeSlot(start=slot_start, end=slot_end))

            if len(slots) >= max_slots:
                return slots

    return slots


async def create_calendar_event(
    student_name: str,
    grade: str,
    subject: str,
    slot: TimeSlot,
) -> str:
    """
    Google Calendarにイベントを作成してイベントIDを返す。
    """
    service = _get_service()
    calendar_id = os.environ["GOOGLE_CALENDAR_ID"]

    event = {
        "summary": f"【塾】{student_name}（{grade}）{subject}",
        "description": f"生徒: {student_name}\n学年: {grade}\n科目: {subject}",
        "start": {
            "dateTime": slot.start.isoformat(),
            "timeZone": "Asia/Tokyo",
        },
        "end": {
            "dateTime": slot.end.isoformat(),
            "timeZone": "Asia/Tokyo",
        },
    }

    created = (
        service.events()
        .insert(calendarId=calendar_id, body=event)
        .execute()
    )
    return created["id"]
