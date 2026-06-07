"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// 保護者向けナビゲーション
const parentNav = [
  { href: "/chat", label: "チャット", icon: "💬" },
  { href: "/calendar", label: "予約", icon: "📅" },
  { href: "/mypage", label: "マイページ", icon: "👤" },
];

// 塾長・講師向けナビゲーション
const staffNav = [
  { href: "/dashboard", label: "ダッシュボード", icon: "📊" },
  { href: "/students", label: "生徒一覧", icon: "👥" },
];

interface NavBarProps {
  role?: "parent" | "staff";
}

export function NavBar({ role = "parent" }: NavBarProps) {
  const pathname = usePathname();
  const nav = role === "staff" ? staffNav : parentNav;

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 safe-area-inset-bottom">
      <div className="flex items-center justify-around max-w-lg mx-auto px-2 py-2">
        {nav.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-0.5 px-4 py-1 rounded-xl transition-colors ${
                active
                  ? "text-accent"
                  : "text-gray-400 hover:text-navy-500"
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-xs font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
