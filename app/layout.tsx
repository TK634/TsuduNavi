import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TsuduNavi — 塾向けAIエージェント",
  description: "体験授業予約・保護者連絡・退塾リスク検知を自動化するSaaS",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "TsuduNavi",
  },
};

export const viewport: Viewport = {
  themeColor: "#1e3a5f",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="antialiased bg-gray-50 text-gray-900 font-sans">
        {children}
      </body>
    </html>
  );
}
