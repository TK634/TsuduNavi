"use client";

// 認証が必要なため静的プリレンダリングを無効化
export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { getMyBookings, Booking } from "@/lib/api";
import { Header } from "@/components/ui/Header";
import { NavBar } from "@/components/ui/NavBar";
import { signOut } from "@/lib/supabase";

// 予約ステータスの日本語ラベル
const statusLabel: Record<string, string> = {
  confirmed: "予約済み",
  completed: "体験完了",
  cancelled: "キャンセル",
};

const statusColor: Record<string, string> = {
  confirmed: "text-green-600 bg-green-50",
  completed: "text-blue-600 bg-blue-50",
  cancelled: "text-gray-400 bg-gray-100",
};

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MyPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (!data.user) { router.push("/login"); return; }
      setEmail(data.user.email ?? "");

      getMyBookings(data.user.id)
        .then(setBookings)
        .finally(() => setLoading(false));
    });
  }, [router]);

  async function handleLogout() {
    await signOut();
    router.push("/login");
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header title="マイページ" />

      <main className="flex-1 overflow-y-auto px-4 pt-5 pb-28 space-y-5">
        {/* プロフィールカード */}
        <div className="bg-navy-500 text-white rounded-2xl px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center text-2xl">
              👤
            </div>
            <div>
              <p className="font-bold">{email}</p>
              <p className="text-xs text-white/60">保護者アカウント</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-4 text-xs text-white/60 hover:text-white underline"
          >
            ログアウト
          </button>
        </div>

        {/* 予約履歴 */}
        <section>
          <h2 className="text-sm font-bold text-gray-500 mb-3 uppercase tracking-wider">
            予約履歴
          </h2>

          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-7 h-7 border-4 border-navy-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : bookings.length === 0 ? (
            <div className="bg-white rounded-2xl p-6 border border-gray-200 text-center">
              <p className="text-gray-400 text-sm">予約履歴がありません</p>
            </div>
          ) : (
            <div className="space-y-3">
              {bookings.map((b) => (
                <div
                  key={b.id}
                  className="bg-white rounded-2xl p-4 border border-gray-200 shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-navy-500">{b.student_name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {b.grade} · {b.subject}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {formatDateTime(b.scheduled_at)}
                      </p>
                    </div>
                    <span
                      className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusColor[b.status] ?? "text-gray-500 bg-gray-100"}`}
                    >
                      {statusLabel[b.status] ?? b.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      <NavBar role="parent" />
    </div>
  );
}
