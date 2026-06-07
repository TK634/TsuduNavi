"use client";

// 認証が必要なため静的プリレンダリングを無効化
export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { getDashboard, DashboardData } from "@/lib/api";
import { Header } from "@/components/ui/Header";
import { NavBar } from "@/components/ui/NavBar";
import { Badge } from "@/components/ui/Badge";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    supabase.auth.getUser().then(({ data: auth }) => {
      if (!auth.user) { router.push("/login"); return; }
    });

    getDashboard()
      .then(setData)
      .catch(() => setError("データの取得に失敗しました"))
      .finally(() => setLoading(false));
  }, [router]);

  const today = new Date().toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  return (
    <div className="flex flex-col min-h-screen">
      <Header title="ダッシュボード" />

      <main className="flex-1 overflow-y-auto px-4 pt-5 pb-28 space-y-5">
        <p className="text-xs text-gray-400">{today}</p>

        {loading && (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-navy-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <p className="text-red-500 text-sm bg-red-50 rounded-xl px-4 py-3">{error}</p>
        )}

        {data && (
          <>
            {/* 退塾リスクアラート */}
            <section>
              <h2 className="text-sm font-bold text-gray-500 mb-3 flex items-center gap-2">
                <span className="text-red-500">⚠️</span>
                退塾リスクアラート
              </h2>

              {data.churn_alerts.length === 0 ? (
                <div className="bg-white rounded-2xl p-4 border border-gray-200 text-sm text-gray-400 text-center">
                  リスクが高い生徒はいません
                </div>
              ) : (
                <div className="space-y-2">
                  {data.churn_alerts.map((alert) => (
                    <div
                      key={alert.student_id}
                      className="bg-white rounded-2xl p-4 border border-red-100 shadow-sm flex items-center justify-between"
                    >
                      <div>
                        <p className="font-bold text-navy-500">{alert.student_name}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          リスクスコア: {alert.score.toFixed(0)}
                        </p>
                      </div>
                      <Badge
                        label={alert.level === "high" ? "高リスク" : alert.level === "medium" ? "中リスク" : "低リスク"}
                        variant={alert.level as "low" | "medium" | "high"}
                      />
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* 今日の予約・授業スケジュール */}
            <section>
              <h2 className="text-sm font-bold text-gray-500 mb-3 flex items-center gap-2">
                <span>📅</span>
                今日の授業スケジュール
              </h2>

              {data.today_bookings.length === 0 ? (
                <div className="bg-white rounded-2xl p-4 border border-gray-200 text-sm text-gray-400 text-center">
                  今日の予約はありません
                </div>
              ) : (
                <div className="space-y-2">
                  {data.today_bookings.map((b) => (
                    <div
                      key={b.id}
                      className="bg-white rounded-2xl p-4 border border-gray-200 shadow-sm flex items-center gap-4"
                    >
                      <div className="text-center min-w-[52px]">
                        <p className="text-lg font-black text-navy-500">
                          {new Date(b.scheduled_at).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}
                        </p>
                      </div>
                      <div className="flex-1">
                        <p className="font-bold text-sm">{b.student_name}</p>
                        <p className="text-xs text-gray-400">{b.grade} · {b.subject}</p>
                      </div>
                      <Badge label="予約済" variant="default" />
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* 未払いリスト */}
            <section>
              <h2 className="text-sm font-bold text-gray-500 mb-3 flex items-center gap-2">
                <span>💴</span>
                未払いリスト
              </h2>

              {data.unpaid_invoices.length === 0 ? (
                <div className="bg-white rounded-2xl p-4 border border-gray-200 text-sm text-gray-400 text-center">
                  未払いはありません
                </div>
              ) : (
                <div className="space-y-2">
                  {data.unpaid_invoices.map((inv) => (
                    <div
                      key={inv.id}
                      className="bg-white rounded-2xl p-4 border border-yellow-100 shadow-sm flex items-center justify-between"
                    >
                      <div>
                        <p className="font-bold text-sm text-navy-500">{inv.student_name}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          期限: {formatDate(inv.due_date)}
                        </p>
                      </div>
                      <p className="font-black text-accent text-base">
                        ¥{inv.amount.toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </main>

      <NavBar role="staff" />
    </div>
  );
}
