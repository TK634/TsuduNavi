import { createClient } from "@supabase/supabase-js";

// ビルド時は環境変数が未設定の場合があるためフォールバック値を使用
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "https://placeholder.supabase.co";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "placeholder-anon-key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export async function getCurrentUser() {
  const { data, error } = await supabase.auth.getUser();
  if (error) return null;
  return data.user;
}

export async function signOut() {
  await supabase.auth.signOut();
}
