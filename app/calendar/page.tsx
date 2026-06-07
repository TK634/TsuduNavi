"use client";

// 認証が必要なため静的プリレンダリングを無効化
export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  getSlots,
  createBooking,
  TimeSlot,
  BookingPayload,
} from "@/lib/api";
import { SlotPicker } from "@/components/calendar/SlotPicker";
import { Header } from "@/components/ui/Header";
import { NavBar } from "@/components/ui/NavBar";
import { Button } from "@/components/ui/Button";

type Step = "select" | "form" | "done";

export default function CalendarPage() {
  const router = useRouter();
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
  const [step, setStep] = useState<Step>("select");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [userId, setUserId] = useState<string | null>(null);

  // フォーム値
  const [studentName, setStudentName] = useState("");
  const [grade, setGrade] = useState("");
  const [subject, setSubject] = useState("");

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (!data.user) { router.push("/login"); return; }
      setUserId(data.user.id);
    });

    getSlots()
      .then(setSlots)
      .catch(() => setError("スロットの取得に失敗しました"))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleBooking() {
    if (!selectedSlot || !userId) return;
    setError("");
    setSubmitting(true);

    const payload: BookingPayload = {
      line_user_id: userId,
      student_name: studentName,
      grade,
      subject,
      slot_start: selectedSlot.start,
      slot_end: selectedSlot.end,
    };

    try {
      await createBooking(payload);
      setStep("done");
    } catch {
      setError("予約に失敗しました。もう一度お試しください。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header title="体験授業を予約" />

      <main className="flex-1 overflow-y-auto px-4 pt-5 pb-28">
        {step === "select" && (
          <>
            <p className="text-sm text-gray-500 mb-4">
              ご希望の日時を選択してください
            </p>

            {loading ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-4 border-navy-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <SlotPicker
                slots={slots}
                selectedSlot={selectedSlot}
                onSelect={setSelectedSlot}
              />
            )}

            {selectedSlot && (
              <div className="mt-6">
                <Button
                  className="w-full py-3 text-base"
                  onClick={() => setStep("form")}
                >
                  この日時で進む →
                </Button>
              </div>
            )}
          </>
        )}

        {step === "form" && (
          <>
            <button
              onClick={() => setStep("select")}
              className="flex items-center gap-1 text-sm text-navy-500 mb-4"
            >
              ← 日時を選び直す
            </button>

            <div className="bg-white rounded-2xl p-4 border border-gray-200 mb-5">
              <p className="text-xs text-gray-400 mb-1">選択した日時</p>
              <p className="font-bold text-navy-500 text-sm">
                {new Date(selectedSlot!.start).toLocaleString("ja-JP", {
                  month: "long",
                  day: "numeric",
                  weekday: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                〜{" "}
                {new Date(selectedSlot!.end).toLocaleTimeString("ja-JP", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">
                  お子さまのお名前
                </label>
                <input
                  type="text"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  placeholder="山田 太郎"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm outline-none focus:border-navy-500 focus:ring-1 focus:ring-navy-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">
                  学年
                </label>
                <select
                  value={grade}
                  onChange={(e) => setGrade(e.target.value)}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm outline-none focus:border-navy-500 bg-white"
                >
                  <option value="">選択してください</option>
                  {["小1","小2","小3","小4","小5","小6","中1","中2","中3","高1","高2","高3"].map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">
                  受講希望科目
                </label>
                <select
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm outline-none focus:border-navy-500 bg-white"
                >
                  <option value="">選択してください</option>
                  {["国語","数学・算数","英語","理科","社会","その他"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>

            {error && (
              <p className="text-red-500 text-xs bg-red-50 rounded-xl px-3 py-2 mt-3">
                {error}
              </p>
            )}

            <Button
              className="w-full py-3 text-base mt-6"
              onClick={handleBooking}
              disabled={!studentName || !grade || !subject || submitting}
            >
              {submitting ? "予約中..." : "予約を確定する"}
            </Button>
          </>
        )}

        {step === "done" && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center text-3xl">
              ✅
            </div>
            <h2 className="text-xl font-bold text-navy-500">予約完了！</h2>
            <p className="text-sm text-gray-500 text-center leading-relaxed">
              ご予約ありがとうございます。<br />
              確認のご連絡をお送りします。
            </p>
            <Button
              variant="secondary"
              className="mt-4"
              onClick={() => {
                setStep("select");
                setSelectedSlot(null);
                setStudentName("");
                setGrade("");
                setSubject("");
              }}
            >
              別の日時も予約する
            </Button>
          </div>
        )}
      </main>

      <NavBar role="parent" />
    </div>
  );
}
