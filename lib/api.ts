// juku-agent FastAPI バックエンドへのAPIクライアント

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── チャット ─────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  message: string;
  stage: string;
}

export async function sendChatMessage(
  lineUserId: string,
  content: string
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ line_user_id: lineUserId, content }),
  });
}

// ── 空き時間スロット ──────────────────────────────────────────────────────

export interface TimeSlot {
  start: string;
  end: string;
}

export async function getSlots(): Promise<TimeSlot[]> {
  return request<TimeSlot[]>("/api/slots");
}

// ── 予約 ──────────────────────────────────────────────────────────────────

export interface BookingPayload {
  line_user_id: string;
  student_name: string;
  grade: string;
  subject: string;
  slot_start: string;
  slot_end: string;
}

export interface Booking {
  id: string;
  student_name: string;
  grade: string;
  subject: string;
  scheduled_at: string;
  status: string;
}

export async function createBooking(payload: BookingPayload): Promise<Booking> {
  return request<Booking>("/api/bookings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMyBookings(lineUserId: string): Promise<Booking[]> {
  return request<Booking[]>(`/api/bookings?line_user_id=${lineUserId}`);
}

// ── 生徒一覧（塾長・講師向け） ────────────────────────────────────────────

export interface Student {
  id: string;
  name: string;
  grade: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high";
  attendance_rate?: number;
  subjects?: string[];
}

export async function getStudents(): Promise<Student[]> {
  return request<Student[]>("/api/students");
}

// ── ダッシュボード ────────────────────────────────────────────────────────

export interface DashboardData {
  churn_alerts: {
    student_id: string;
    student_name: string;
    score: number;
    level: string;
  }[];
  today_bookings: Booking[];
  unpaid_invoices: {
    id: string;
    student_name: string;
    amount: number;
    due_date: string;
  }[];
}

export async function getDashboard(): Promise<DashboardData> {
  return request<DashboardData>("/api/dashboard");
}
