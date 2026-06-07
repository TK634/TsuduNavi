"use client";

// 認証が必要なため静的プリレンダリングを無効化
export const dynamic = "force-dynamic";

import { useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabase";
import { sendChatMessage, ChatMessage } from "@/lib/api";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { Header } from "@/components/ui/Header";
import { NavBar } from "@/components/ui/NavBar";
import { signOut } from "@/lib/supabase";
import { useRouter } from "next/navigation";

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // ログインユーザーの取得
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (!data.user) {
        router.push("/login");
        return;
      }
      setUserId(data.user.id);
      // 初回メッセージ（AI挨拶）
      setMessages([
        {
          role: "assistant",
          content:
            "こんにちは！TsuduNaviです😊\n体験授業のご予約や、塾についてのご質問など、お気軽にどうぞ。",
          timestamp: new Date().toISOString(),
        },
      ]);
    });
  }, [router]);

  // Supabaseリアルタイム購読（messages テーブルを想定）
  useEffect(() => {
    if (!userId) return;

    const channel = supabase
      .channel(`chat:${userId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "messages",
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          const row = payload.new as {
            role: string;
            content: string;
            created_at: string;
          };
          // assistantメッセージのみリアルタイムで追記
          if (row.role === "assistant") {
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: row.content,
                timestamp: row.created_at,
              },
            ]);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId]);

  // 新しいメッセージが来たら最下部へスクロール
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(text: string) {
    if (!userId) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    try {
      const res = await sendChatMessage(userId, text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.message,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "申し訳ありません。エラーが発生しました。もう一度お試しください。",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function handleLogout() {
    await signOut();
    router.push("/login");
  }

  return (
    <div className="flex flex-col h-screen">
      <Header
        title="AIチャット"
        right={
          <button
            onClick={handleLogout}
            className="text-xs text-white/70 hover:text-white"
          >
            ログアウト
          </button>
        }
      />

      {/* メッセージ一覧 */}
      <div className="flex-1 overflow-y-auto px-4 pt-4 pb-2 bg-gray-50">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {sending && (
          <div className="flex items-end gap-2 mb-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-navy-500 flex items-center justify-center text-white text-xs font-bold">
              AI
            </div>
            <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100">
              <span className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:300ms]" />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={handleSend} disabled={sending} />
      <NavBar role="parent" />
    </div>
  );
}
