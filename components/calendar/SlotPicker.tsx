"use client";

import { TimeSlot } from "@/lib/api";

interface SlotPickerProps {
  slots: TimeSlot[];
  selectedSlot: TimeSlot | null;
  onSelect: (slot: TimeSlot) => void;
}

// 日時を「M/D（曜）HH:MM」形式にフォーマット
function formatSlot(iso: string) {
  const d = new Date(iso);
  const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
  const month = d.getMonth() + 1;
  const day = d.getDate();
  const weekday = weekdays[d.getDay()];
  const hour = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return { date: `${month}/${day}（${weekday}）`, time: `${hour}:${min}` };
}

export function SlotPicker({ slots, selectedSlot, onSelect }: SlotPickerProps) {
  if (slots.length === 0) {
    return (
      <p className="text-center text-gray-400 py-8 text-sm">
        現在予約可能な空き時間がありません
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3">
      {slots.map((slot, i) => {
        const start = formatSlot(slot.start);
        const end = formatSlot(slot.end);
        const isSelected =
          selectedSlot?.start === slot.start && selectedSlot?.end === slot.end;

        return (
          <button
            key={i}
            onClick={() => onSelect(slot)}
            className={`w-full flex items-center justify-between px-4 py-4 rounded-2xl border-2 transition-all active:scale-98 ${
              isSelected
                ? "border-accent bg-orange-50 shadow-md"
                : "border-gray-200 bg-white hover:border-navy-500"
            }`}
          >
            <div className="text-left">
              <p className={`text-sm font-bold ${isSelected ? "text-accent" : "text-navy-500"}`}>
                {start.date}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {start.time} 〜 {end.time}
              </p>
            </div>
            <div
              className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                isSelected ? "border-accent bg-accent" : "border-gray-300"
              }`}
            >
              {isSelected && (
                <svg viewBox="0 0 12 12" fill="white" className="w-3 h-3">
                  <polyline points="1,6 4.5,9.5 11,3" strokeWidth="2" stroke="white" fill="none" strokeLinecap="round" />
                </svg>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
