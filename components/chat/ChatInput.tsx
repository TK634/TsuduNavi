"use client";

import { FormEvent, useState } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 px-3 py-3 bg-white border-t border-gray-200"
    >
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          // Ctrl/Cmd + Enter で送信
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            handleSubmit(e as unknown as FormEvent);
          }
        }}
        rows={1}
        placeholder="メッセージを入力..."
        disabled={disabled}
        className="flex-1 resize-none rounded-2xl border border-gray-300 px-4 py-2.5 text-sm outline-none focus:border-navy-500 focus:ring-1 focus:ring-navy-500 disabled:opacity-50 max-h-28 overflow-y-auto"
        style={{ minHeight: "42px" }}
      />
      <button
        type="submit"
        disabled={!text.trim() || disabled}
        className="flex-shrink-0 w-10 h-10 rounded-full bg-accent text-white flex items-center justify-center disabled:opacity-40 active:scale-95 transition-transform"
        aria-label="送信"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 rotate-90">
          <path d="M2 21L23 12 2 3v7l15 2-15 2z" />
        </svg>
      </button>
    </form>
  );
}
