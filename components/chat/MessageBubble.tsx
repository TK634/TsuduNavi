import { ChatMessage } from "@/lib/api";

interface MessageBubbleProps {
  message: ChatMessage;
}

// タイムスタンプを「HH:MM」形式にフォーマット
function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-end gap-2 mb-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* アバター（AIのみ） */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-navy-500 flex items-center justify-center text-white text-xs font-bold">
          AI
        </div>
      )}

      <div className={`flex flex-col gap-1 max-w-[75%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm ${
            isUser
              ? "bg-accent text-white rounded-br-sm"
              : "bg-white text-gray-800 rounded-bl-sm border border-gray-100"
          }`}
        >
          {/* 改行を保持して表示 */}
          {message.content.split("\n").map((line, i) => (
            <span key={i}>
              {line}
              {i < message.content.split("\n").length - 1 && <br />}
            </span>
          ))}
        </div>
        <span className="text-[10px] text-gray-400 px-1">
          {formatTime(message.timestamp)}
        </span>
      </div>
    </div>
  );
}
