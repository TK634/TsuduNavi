import { redirect } from "next/navigation";

// ルートはログイン画面へリダイレクト
export default function RootPage() {
  redirect("/login");
}
