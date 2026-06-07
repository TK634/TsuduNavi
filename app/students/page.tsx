"use client";

// 認証が必要なため静的プリレンダリングを無効化
export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { getStudents, Student } from "@/lib/api";
import { Header } from "@/components/ui/Header";
import { NavBar } from "@/components/ui/NavBar";
import { Badge } from "@/components/ui/Badge";

const riskLabels: Record<string, string> = {
  low: "低リスク",
  medium: "中リスク",
  high: "高リスク",
};

export default function StudentsPage() {
  const router = useRouter();
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (!data.user) { router.push("/login"); return; }
    });

    getStudents()
      .then(setStudents)
      .catch(() => setError("生徒データの取得に失敗しました"))
      .finally(() => setLoading(false));
  }, [router]);

  // 氏名・学年での絞り込み
  const filtered = students.filter((s) => {
    const q = search.trim();
    if (!q) return true;
    return (
      s.name?.includes(q) ||
      s.grade?.includes(q)
    );
  });

  // 高リスク → 中リスク → 低リスク の順にソート
  const riskOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const sorted = [...filtered].sort(
    (a, b) => (riskOrder[a.risk_level] ?? 3) - (riskOrder[b.risk_level] ?? 3)
  );

  return (
    <div className="flex flex-col min-h-screen">
      <Header title="生徒一覧" />

      <main className="flex-1 overflow-y-auto pb-28">
        {/* 検索バー */}
        <div className="px-4 pt-4 pb-3 bg-white border-b border-gray-100 sticky top-0 z-10">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="氏名・学年で検索..."
            className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-navy-500 focus:ring-1 focus:ring-navy-500"
          />
        </div>

        <div className="px-4 pt-3">
          {loading && (
            <div className="flex justify-center py-12">
              <div className="w-8 h-8 border-4 border-navy-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {error && (
            <p className="text-red-500 text-sm bg-red-50 rounded-xl px-4 py-3">{error}</p>
          )}

          {!loading && sorted.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-12">
              該当する生徒が見つかりません
            </p>
          )}

          <div className="space-y-3">
            {sorted.map((student) => (
              <div
                key={student.id}
                className={`bg-white rounded-2xl p-4 border shadow-sm ${
                  student.risk_level === "high"
                    ? "border-red-200"
                    : student.risk_level === "medium"
                    ? "border-yellow-200"
                    : "border-gray-200"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-bold text-navy-500">{student.name ?? "名前未設定"}</p>
                      <Badge
                        label={riskLabels[student.risk_level] ?? student.risk_level}
                        variant={student.risk_level as "low" | "medium" | "high"}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{student.grade}</p>
                    {student.subjects && student.subjects.length > 0 && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        受講科目: {student.subjects.join("・")}
                      </p>
                    )}
                  </div>

                  {/* 出席率 */}
                  {student.attendance_rate !== undefined && (
                    <div className="text-right">
                      <p className="text-2xl font-black text-navy-500">
                        {Math.round(student.attendance_rate)}%
                      </p>
                      <p className="text-[10px] text-gray-400">出席率</p>
                    </div>
                  )}
                </div>

                {/* リスクスコアバー */}
                <div className="mt-3">
                  <div className="flex items-center justify-between text-[10px] text-gray-400 mb-1">
                    <span>退塾リスクスコア</span>
                    <span>{student.risk_score.toFixed(0)} / 100</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        student.risk_level === "high"
                          ? "bg-red-400"
                          : student.risk_level === "medium"
                          ? "bg-yellow-400"
                          : "bg-green-400"
                      }`}
                      style={{ width: `${Math.min(student.risk_score, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      <NavBar role="staff" />
    </div>
  );
}
