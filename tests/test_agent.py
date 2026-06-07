"""
agent.py の情報抽出ロジックのユニットテスト。
外部APIはモックしてオフラインで実行できる。
"""

import pytest

from app.agent import (
    _extract_grade,
    _extract_schedule,
    _extract_slot_selection,
    _extract_subject,
    _format_collected,
)
from app.models import CollectedData


# ── 学年抽出 ─────────────────────────────────────────────────────────────


class TestExtractGrade:
    def test_小学生_短縮形(self):
        assert _extract_grade("小3の子です") == "小3"

    def test_小学生_フル表記(self):
        assert _extract_grade("小学4年生です") == "小4"

    def test_中学生(self):
        assert _extract_grade("中学2年生です") == "中2"

    def test_高校生(self):
        assert _extract_grade("高1です") == "高1"

    def test_高校生_フル(self):
        assert _extract_grade("高校3年生です") == "高3"

    def test_学年なし(self):
        assert _extract_grade("よろしくお願いします") is None

    def test_文中に含まれる(self):
        assert _extract_grade("うちの子は今中3なんですが") == "中3"


# ── 科目抽出 ─────────────────────────────────────────────────────────────


class TestExtractSubject:
    def test_数学(self):
        assert _extract_subject("数学を教えてほしいです") == "数学"

    def test_英語(self):
        assert _extract_subject("英語が苦手なので") == "英語"

    def test_算数(self):
        assert _extract_subject("算数をお願いしたい") == "算数"

    def test_国語(self):
        assert _extract_subject("国語の読解が苦手です") == "国語"

    def test_理科(self):
        assert _extract_subject("理科を習いたい") == "理科"

    def test_科目なし(self):
        assert _extract_subject("よろしくお願いします") is None


# ── 日程抽出 ─────────────────────────────────────────────────────────────


class TestExtractSchedule:
    def test_曜日と時間帯(self):
        days, time = _extract_schedule("月曜と水曜の午後がいいです")
        assert "月" in days
        assert "水" in days
        assert time == "午後"

    def test_夕方(self):
        _, time = _extract_schedule("夕方がいいですね")
        assert time == "夕方"

    def test_午前(self):
        _, time = _extract_schedule("午前中にお願いしたい")
        assert time == "午前"

    def test_夜(self):
        _, time = _extract_schedule("夜の時間帯で")
        assert time == "夜"

    def test_曜日なし_時間帯のみ(self):
        days, time = _extract_schedule("午後ならどこでも")
        assert days == []
        assert time == "午後"

    def test_土曜(self):
        days, _ = _extract_schedule("土曜日がいいです")
        assert "土" in days


# ── スロット選択抽出 ──────────────────────────────────────────────────────


class TestExtractSlotSelection:
    def test_丸数字1(self):
        assert _extract_slot_selection("①を希望します") == 0

    def test_丸数字2(self):
        assert _extract_slot_selection("②でお願いします") == 1

    def test_丸数字3(self):
        assert _extract_slot_selection("③がいいです") == 2

    def test_数字番号(self):
        assert _extract_slot_selection("1番でお願いします") == 0

    def test_選択なし(self):
        assert _extract_slot_selection("ありがとうございます") is None


# ── 収集データフォーマット ────────────────────────────────────────────────


class TestFormatCollected:
    def test_全項目あり(self):
        data = CollectedData(
            grade="中3",
            subject="数学",
            preferred_days=["月", "水"],
            preferred_time="午後",
        )
        result = _format_collected(data)
        assert "中3" in result
        assert "数学" in result
        assert "月" in result
        assert "午後" in result

    def test_未収集(self):
        result = _format_collected(CollectedData())
        assert "未収集" in result
