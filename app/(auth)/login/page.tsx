"use client";

export const dynamic = "force-dynamic";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/Button";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      setError("メールアドレスまたはパスワードが正しくありません");
      setLoading(false);
      return;
    }

    // ロールに応じて遷移（今後はuser_metadataのroleで判断）
    router.push("/chat");
  }

  return (
    <div className="min-h-screen bg-navy-500 flex flex-col items-center justify-center px-6">
      {/* ロゴエリア */}
      <div className="mb-10 text-center">
        <div className="text-4xl font-black text-white tracking-tight">
          TsuduNavi
        </div>
        <p className="text-navy-100 text-sm mt-2">塾向けAIエージェント</p>
      </div>

      {/* フォームカード */}
      <div className="w-full max-w-sm bg-white rounded-3xl shadow-xl p-6">
        <h2 className="text-navy-500 font-bold text-lg mb-5">ログイン</h2>

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">
              メールアドレス
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="example@email.com"
              required
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm outline-none focus:border-navy-500 focus:ring-1 focus:ring-navy-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">
              パスワード
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm outline-none focus:border-navy-500 focus:ring-1 focus:ring-navy-500"
            />
          </div>

          {error && (
            <p className="text-red-500 text-xs bg-red-50 rounded-xl px-3 py-2">
              {error}
            </p>
          )}

          <Button type="submit" disabled={loading} className="w-full py-3 text-base mt-1">
            {loading ? "ログイン中..." : "ログイン"}
          </Button>
        </form>
      </div>

      <p className="text-navy-100 text-xs mt-6">
        アカウントの発行は塾長にお問い合わせください
      </p>
    </div>
  );
}
